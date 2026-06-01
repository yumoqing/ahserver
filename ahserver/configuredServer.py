import os,sys
from sys import platform
import time
import ssl
import asyncio
from socket import *
from aiohttp import web

from appPublic.folderUtils import ProgramPath, listFolder, listFile
from appPublic.dictObject import DictObject
from appPublic.jsonConfig import getConfig
from appPublic.log import info, debug, warning, error, critical, exception
from appPublic.registerfunction import RegisterFunction

from sqlor.dbpools import DBPools

from .processorResource import ProcessorResource
from .auth_api import AuthAPI
from .myTE import setupTemplateEngine
from .globalEnv import initEnv
from .serverenv import ServerEnv
from .filestorage import TmpFileRecord
from .loadplugins import load_plugins
from .real_ip import real_ip_middleware
from .hotreload import HotReloader, get_i18n_paths, hot_reload_task, hot_reload_handler

startup_coros = []
cleanupctx_coros = []

def add_startup(coro):
	startup_coros.append(coro)

def add_cleanupctx(coro):
	cleanupctx_coros.append(coro)

class AHApp(web.Application):
	def __init__(self, *args, **kw):
		if not kw.get('client_max_size'):
			kw['client_max_size'] = 1024000000
		debug(f"client_max_size={kw['client_max_size']}")
		super().__init__(*args, **kw)
		self.user_data = DictObject()
		self.middlewares.insert(0, real_ip_middleware())

	def set_data(self, k, v):
		self.user_data[k] = v
	
	def get_data(self, k):
		return self.user_data.get(k)

class ConfiguredServer:
	def __init__(self, auth_klass=AuthAPI, workdir=None, app=None):
		self.auth_klass = auth_klass
		self.workdir = workdir
		if self.workdir is not None:
			pp = ProgramPath()
			config = getConfig(self.workdir,
					{'workdir':self.workdir,'ProgramPath':pp})
		else:
			config = getConfig()
		if config.databases:
			DBPools(config.databases)
		self.config = config
		initEnv()
		setupTemplateEngine()
		client_max_size = 1024000000
		if config.website.client_max_size:
			client_max_size = config.website.client_max_size

		if app:
			self.app = app
		else:
			self.app = AHApp(client_max_size=client_max_size)
		load_plugins(self.workdir)
		g = ServerEnv()
		g.workdir = workdir
		g.cssfiles = self.get_css_files
		g.jsfiles = self.get_js_files
	
	def get_filetype_files(self, suffix):
		paths = self.config.website.paths
		fs = []
		for p, part in paths:
			pos = len(p)
			fs += [f[pos:] for f in listFile(p, suffixs=[suffix])]
			if part == '':
				subpaths = listFolder(p)
				for sp in subpaths:
					fs += [f[pos:] for f in listFile(sp, suffixs=[suffix])]
		return fs

	def get_css_files(self):
		return [ f for f in self.get_filetype_files('.css') if not f.startswith('/bricks') ]

	def get_js_files(self):
		return [ f for f in self.get_filetype_files('.js') if not f.startswith('/bricks') ]

	async def build_app(self):
		rf = RegisterFunction()
		await rf.exe('ahapp_built', self.app)
		auth = self.auth_klass()
		await auth.setupAuth(self.app)
		return self.app
		
	def run(self, port=None):
		config = getConfig()
		self.configPath(config)
		a = TmpFileRecord()
		ssl_context = None
		if port is None:
			port = config.website.port or 8080
		if config.website.ssl:
			ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
			ssl_context.load_cert_chain(config.website.ssl.crtfile,
							config.website.ssl.keyfile)
		reuse_port = None
		if platform != 'win32':
			reuse_port = True
		print('reuse_port=', reuse_port)
		[ self.app.on_startup.append(c) for c in startup_coros ]
		[ self.app.cleanup_ctx.append(c) for c in cleanupctx_coros ]

		# Hot reload setup
		hot_reload_cfg = config.get('hot_reload', False)
		if hot_reload_cfg:
			interval = 2
			if isinstance(hot_reload_cfg, dict):
				if not hot_reload_cfg.get('enabled', True):
					hot_reload_cfg = False
				else:
					interval = hot_reload_cfg.get('interval', 2)
			if hot_reload_cfg:
				workdir = self.workdir or os.getcwd()
				config_path = os.path.join(workdir, 'conf', 'config.json')
				i18n_paths = get_i18n_paths(workdir)
				reloader = HotReloader(config_path, i18n_paths)
				reloader.set_interval(interval)
				# Register HTTP endpoint for manual cache flush
				self.app.router.add_get('/__hot_reload__', hot_reload_handler)
				async def _hot_reload_startup(app):
					task = asyncio.create_task(hot_reload_task(app, reloader))
					app['hot_reload_task'] = task
				async def _hot_reload_cleanup(app):
					task = app.get('hot_reload_task')
					if task:
						task.cancel()
						try:
							await task
						except asyncio.CancelledError:
							pass
				self.app.on_startup.append(_hot_reload_startup)
				self.app.on_cleanup.append(_hot_reload_cleanup)
				print(f'hot_reload enabled, interval={interval}s, endpoint=GET /__hot_reload__')

		web.run_app(self.build_app(),host=config.website.host or '0.0.0.0',
						port=port,
						reuse_port=reuse_port,
						ssl_context=ssl_context)

	def configPath(self,config):
		for p,prefix in config.website.paths:
			res = ProcessorResource(prefix, p, show_index=True,
							follow_symlinks=True,
							indexes=config.website.indexes,
							processors=config.website.processors)
			self.app.router.register_resource(res)
	

