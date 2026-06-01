"""
ahserver hot-reload module.

Watches file mtimes and triggers reload of cached resources:
- config.json (JsonConfig singleton)
- i18n files (MiniI18N singleton)
- Jinja2 template cache (auto_reload already handles this)

Module caches (rbac/pricing/uapi/llmage) can be cleared via:
- HTTP endpoint: GET /__hot_reload__ (triggers all workers via signal file)
- Automatic when config.json changes

Cross-process cache invalidation (reuse_port multi-process):
- GET /__hot_reload__ writes to /tmp/.sage_cache_invalidate signal file
- All workers detect signal file mtime change within their check interval
- Each worker independently clears its own caches
- No cross-process IPC or Redis needed

Multi-process safe: each process independently checks mtimes via stat(),
no cross-process coordination needed. When a file changes on disk,
all processes detect it on their next check cycle.

Usage in conf/config.json:
{
    "hot_reload": {
        "enabled": true,
        "interval": 2
    }
}

Or simply:
{
    "hot_reload": true
}
"""

import os
import time
import asyncio
from appPublic.log import info, debug, warning


class FileWatcher:
    """Track file mtimes and detect changes."""

    def __init__(self):
        self._mtimes = {}

    def check(self, paths):
        """Check if any of the given paths have changed.
        
        Args:
            paths: list of absolute file paths to watch
            
        Returns:
            list of changed file paths (empty if none changed)
        """
        changed = []
        for path in paths:
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            old_mtime = self._mtimes.get(path)
            if old_mtime is None:
                self._mtimes[path] = mtime
            elif mtime > old_mtime:
                self._mtimes[path] = mtime
                changed.append(path)
        return changed


SIGNAL_FILE = '/tmp/.sage_cache_invalidate'


class HotReloader:
    """Hot-reload cached resources when source files change.
    
    Each process runs its own HotReloader instance. Since all processes
    share the same filesystem, mtime-based detection works independently
    in each process without any cross-process communication.
    """

    def __init__(self, config_path, i18n_paths=None):
        self._watcher = FileWatcher()
        self._config_path = config_path
        self._i18n_paths = i18n_paths or []
        self._last_check = 0
        self._interval = 2  # seconds between checks
        # Record current signal file mtime to avoid false trigger on startup
        try:
            self._last_signal_mtime = os.path.getmtime(SIGNAL_FILE)
        except OSError:
            self._last_signal_mtime = 0

    def set_interval(self, interval):
        self._interval = interval

    def _should_check(self):
        now = time.time()
        if now - self._last_check < self._interval:
            return False
        self._last_check = now
        return True

    def _check_signal_file(self):
        """Check if cache invalidation signal file was updated."""
        try:
            mtime = os.path.getmtime(SIGNAL_FILE)
            if mtime > self._last_signal_mtime:
                self._last_signal_mtime = mtime
                return True
        except OSError:
            pass
        return False

    def check_and_reload(self):
        """Check for file changes and reload if needed.
        
        Returns:
            dict with keys 'config', 'i18n', 'signal' indicating what was reloaded
        """
        if not self._should_check():
            return {}

        reloaded = {}

        # Check config.json
        config_changed = self._watcher.check([self._config_path])
        if config_changed:
            self._reload_config()
            reloaded['config'] = True

        # Check i18n files
        if self._i18n_paths:
            i18n_changed = self._watcher.check(self._i18n_paths)
            if i18n_changed:
                self._reload_i18n()
                reloaded['i18n'] = True

        # Check signal file (cross-process cache invalidation)
        if self._check_signal_file():
            invalidate_all_caches()
            reloaded['signal'] = True

        return reloaded

    def _reload_config(self):
        """Clear JsonConfig singleton so next getConfig() call reloads from disk.
        Also clear all module caches since config changes may affect them.
        """
        try:
            from appPublic.jsonConfig import JsonConfig
            # SingletonDecorator stores instance as .instance
            JsonConfig.instance = None
            info('[hot_reload] config.json changed, cache cleared')
            # Also clear module caches since config may affect module_cache settings
            invalidate_all_caches()
        except Exception as e:
            warning(f'[hot_reload] failed to reload config: {e}')

    def _reload_i18n(self):
        """Clear MiniI18N singleton and ServerEnv cache."""
        try:
            from appPublic.i18n import MiniI18N
            MiniI18N.instance = None
            # Clear cached i18n on ServerEnv
            try:
                from .serverenv import ServerEnv
                g = ServerEnv()
                if hasattr(g, 'myi18n'):
                    del g.myi18n
            except Exception:
                pass
            info('[hot_reload] i18n files changed, cache cleared')
        except Exception as e:
            warning(f'[hot_reload] failed to reload i18n: {e}')


def get_i18n_paths(workdir=None):
    """Collect all i18n msg.txt file paths for watching."""
    if workdir is None:
        workdir = os.getcwd()
    i18n_dir = os.path.join(workdir, 'i18n')
    paths = []
    if os.path.isdir(i18n_dir):
        for lang in os.listdir(i18n_dir):
            msg_file = os.path.join(i18n_dir, lang, 'msg.txt')
            if os.path.isfile(msg_file):
                paths.append(msg_file)
    return paths


async def hot_reload_task(app, reloader):
    """Background task that periodically checks for file changes.
    
    Added to app.on_startup when hot_reload is enabled.
    """
    info(f'[hot_reload] started, interval={reloader._interval}s')
    try:
        while True:
            await asyncio.sleep(reloader._interval)
            reloaded = reloader.check_and_reload()
            if reloaded:
                info(f'[hot_reload] reloaded: {list(reloaded.keys())}')
    except asyncio.CancelledError:
        info('[hot_reload] stopped')
        raise


def invalidate_all_caches():
    """Clear all module caches (rbac/pricing/uapi/llmage).
    
    Called automatically when config.json changes, or manually via
    GET /__hot_reload__ endpoint.
    
    Each module cache is cleared independently with try/except to
    prevent one module's failure from blocking others.
    """
    cleared = []
    
    # rbac: UserPermissions is NOT a singleton — the actual instance is
    # stored on ServerEnv by load_rbac(). Must get that instance, not
    # create a new one (which would have empty caches).
    try:
        from ahserver.serverenv import ServerEnv
        g = ServerEnv()
        up = getattr(g, 'userpermissions', None)
        if up is not None:
            up.ur_caches.clear()
            up.invalidate_rp_cache()
            cleared.append('rbac')
        else:
            debug('[hot_reload] rbac: userpermissions not found on ServerEnv')
    except Exception as e:
        debug(f'[hot_reload] rbac cache clear skipped: {e}')
    
    # pricing: PricingProgram class-level pricing_data dict
    try:
        from pricing.pricing import PricingProgram
        PricingProgram.pricing_data.clear()
        cleared.append('pricing')
    except Exception as e:
        debug(f'[hot_reload] pricing cache clear skipped: {e}')
    
    # uapi: UAPIData singleton (@SingletonDecorator) with 3 cache dicts
    try:
        from uapi.apidata import UAPIData
        ud = UAPIData()
        ud.apidata.clear()
        ud.org_users.clear()
        ud.apikeys.clear()
        cleared.append('uapi')
    except Exception as e:
        debug(f'[hot_reload] uapi cache clear skipped: {e}')
    
    # llmage: module-level _uapi_cache and _uapiio_cache
    try:
        from llmage.utils import invalidate_uapi_cache
        invalidate_uapi_cache()  # clears both _uapi_cache and _uapiio_cache
        cleared.append('llmage')
    except Exception as e:
        debug(f'[hot_reload] llmage cache clear skipped: {e}')
    
    if cleared:
        info(f'[hot_reload] cleared caches: {cleared}')
    return cleared


async def hot_reload_handler(request):
    """HTTP endpoint handler for GET /__hot_reload__.
    
    Triggers cache invalidation across all workers via signal file.
    Each worker detects the signal file change within its check interval
    and clears its own caches.
    
    Returns JSON with confirmation that signal was sent.
    """
    from aiohttp import web
    
    # Write signal file - all workers will detect this
    with open(SIGNAL_FILE, 'w') as f:
        f.write(str(time.time()))
    
    # Also clear current worker's cache immediately
    cleared = invalidate_all_caches()
    
    return web.json_response({
        'status': 'ok',
        'cleared': cleared,
        'message': 'Signal sent to all workers',
        'timestamp': time.time()
    })

