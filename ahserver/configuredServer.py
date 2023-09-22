import os,sys
import time
import ssl
from socket import *
from aiohttp import web

from appPublic.folderUtils import ProgramPath
from appPublic.background import Background
from appPublic.jsonConfig import getConfig
from appPublic.app_logger import AppLogger

from sqlor.dbpools import DBPools

from .processorResource import ProcessorResource
from .auth_api import AuthAPI
from .myTE import setupTemplateEngine
from .globalEnv import initEnv
from .filestorage import TmpFileRecord
from .loadplugins import load_plugins

class ConfiguredServer(AppLogger):
	def __init__(self, auth_klass=AuthAPI, workdir=None):
		self.auth_klass = auth_klass
		self.workdir = workdir
		super().__init__()
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
		client_max_size = 1024 * 10240
		if config.website.client_max_size:
			client_max_size = config.website.client_max_size

		load_plugins(self.workdir)
		self.app = web.Application(client_max_size=client_max_size)
	
	async def init_auth(self):
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

		web.run_app(self.init_auth(),host=config.website.host or '0.0.0.0',
							port=port,
							ssl_context=ssl_context)

	def configPath(self,config):
		for p,prefix in config.website.paths:
			res = ProcessorResource(prefix,p,show_index=True,
							follow_symlinks=True,
							indexes=config.website.indexes,
							processors=config.website.processors)
			self.app.router.register_resource(res)
	
