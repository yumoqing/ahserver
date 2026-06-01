"""
ahserver hot-reload module.

Watches file mtimes and triggers reload of cached resources:
- config.json (JsonConfig singleton)
- i18n files (MiniI18N singleton)
- Jinja2 template cache (auto_reload already handles this)

Module cache invalidation via EventDispatcher:
- ahserver dispatches 'hot_reload' event
- Each module binds its own cache-clear handler in load_XXX()
- No coupling: ahserver doesn't import or know about any module

Trigger sources:
- HTTP endpoint: GET /__hot_reload__ (triggers all workers via signal file)
- config.json mtime change (auto-detected by FileWatcher)
- Signal file mtime change (cross-process, reuse_port multi-worker)

Cross-process cache invalidation (reuse_port multi-process):
- GET /__hot_reload__ writes to /tmp/.sage_cache_invalidate signal file
- All workers detect signal file mtime change within their check interval
- Each worker dispatches 'hot_reload' event independently

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
                debug(f'[hot_reload] initial mtime for {path}: {mtime}')
            elif mtime > old_mtime:
                self._mtimes[path] = mtime
                changed.append(path)
                debug(f'[hot_reload] changed: {path} (mtime {old_mtime} -> {mtime})')
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
                debug(f'[hot_reload] signal file changed, mtime: {mtime}')
                return True
        except OSError:
            pass
        return False

    def check_and_reload(self):
        """Check for file changes and reload if needed.
        
        Returns:
            dict with keys 'config', 'i18n', 'signal' indicating what was reloaded.
            Caller should dispatch 'hot_reload' event if dict is non-empty.
        """
        if not self._should_check():
            return {}

        reloaded = {}

        # Check config.json
        config_changed = self._watcher.check([self._config_path])
        if config_changed:
            debug(f'[hot_reload] config changed: {config_changed}')
            self._reload_config()
            reloaded['config'] = True

        # Check i18n files
        if self._i18n_paths:
            i18n_changed = self._watcher.check(self._i18n_paths)
            if i18n_changed:
                debug(f'[hot_reload] i18n changed: {i18n_changed}')
                self._reload_i18n()
                reloaded['i18n'] = True

        # Check signal file (cross-process cache invalidation)
        if self._check_signal_file():
            reloaded['signal'] = True

        if reloaded:
            debug(f'[hot_reload] check_and_reload result: {reloaded}')

        return reloaded

    def _reload_config(self):
        """Clear JsonConfig singleton so next getConfig() call reloads from disk."""
        try:
            from appPublic.jsonConfig import JsonConfig
            debug('[hot_reload] clearing JsonConfig singleton')
            # SingletonDecorator stores instance as .instance
            JsonConfig.instance = None
            info('[hot_reload] config.json changed, cache cleared')
        except Exception as e:
            warning(f'[hot_reload] failed to reload config: {e}')

    def _reload_i18n(self):
        """Clear MiniI18N singleton and ServerEnv cache."""
        try:
            from appPublic.i18n import MiniI18N
            debug('[hot_reload] clearing MiniI18N singleton')
            MiniI18N.instance = None
            # Clear cached i18n on ServerEnv
            try:
                from .serverenv import ServerEnv
                g = ServerEnv()
                if hasattr(g, 'myi18n'):
                    del g.myi18n
                    debug('[hot_reload] cleared ServerEnv.myi18n')
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
    Dispatches 'hot_reload' event via EventDispatcher when changes detected.
    """
    from .serverenv import ServerEnv
    dispatcher = ServerEnv().event_dispatcher
    info(f'[hot_reload] started, interval={reloader._interval}s')
    debug(f'[hot_reload] config_path={reloader._config_path}')
    debug(f'[hot_reload] watching {len(reloader._i18n_paths)} i18n paths')
    try:
        while True:
            await asyncio.sleep(reloader._interval)
            reloaded = reloader.check_and_reload()
            if reloaded:
                info(f'[hot_reload] reloaded: {list(reloaded.keys())}')
                # Only dispatch hot_reload event for non-config changes
                # Config-only reload just refreshes JsonConfig singleton, no cache clearing needed
                needs_cache_clear = any(k != 'config' for k in reloaded)
                if needs_cache_clear:
                    debug(f'[hot_reload] dispatching hot_reload event (non-config changes detected)')
                    await dispatcher.dispatch('hot_reload', reloaded)
                else:
                    debug(f'[hot_reload] config-only change, skipping cache clear dispatch')
    except asyncio.CancelledError:
        info('[hot_reload] stopped')
        raise


async def hot_reload_handler(request):
    """HTTP endpoint handler for GET /__hot_reload__.
    
    Triggers cache invalidation across all workers via signal file,
    and immediately dispatches 'hot_reload' for the current worker.
    
    Returns JSON with confirmation that signal was sent.
    """
    from aiohttp import web
    from .serverenv import ServerEnv
    
    debug(f'[hot_reload] HTTP endpoint triggered, writing signal to {SIGNAL_FILE}')
    # Write signal file - other workers will detect this
    with open(SIGNAL_FILE, 'w') as f:
        f.write(str(time.time()))
    
    # Dispatch immediately for current worker
    dispatcher = ServerEnv().event_dispatcher
    debug('[hot_reload] HTTP endpoint: dispatching hot_reload event')
    await dispatcher.dispatch('hot_reload', {'source': 'http_endpoint'})
    
    return web.json_response({
        'status': 'ok',
        'message': 'Signal sent to all workers, current worker dispatched hot_reload',
        'timestamp': time.time()
    })
