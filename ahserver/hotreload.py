"""
ahserver hot-reload module.

Watches file mtimes and triggers reload of cached resources:
- config.json (JsonConfig singleton)
- i18n files (MiniI18N singleton)
- Jinja2 template cache (auto_reload already handles this)

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

    def set_interval(self, interval):
        self._interval = interval

    def _should_check(self):
        now = time.time()
        if now - self._last_check < self._interval:
            return False
        self._last_check = now
        return True

    def check_and_reload(self):
        """Check for file changes and reload if needed.
        
        Returns:
            dict with keys 'config', 'i18n' indicating what was reloaded
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

        return reloaded

    def _reload_config(self):
        """Clear JsonConfig singleton so next getConfig() call reloads from disk."""
        try:
            from appPublic.jsonConfig import JsonConfig
            # SingletonDecorator stores instance as .instance
            JsonConfig.instance = None
            info('[hot_reload] config.json changed, cache cleared')
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
