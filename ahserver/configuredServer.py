import os,sys
import ssl
from aiohttp import web

from appPublic.folderUtils import ProgramPath
from appPublic.jsonConfig import getConfig

from sqlor.dbpools import DBPools

from .processorResource import ProcessorResource
from .auth_api import AuthAPI
from .myTE import setupTemplateEngine
from .globalEnv import initEnv

class ConfiguredServer:
	def __init__(self,auth_klass=AuthAPI):
		pp = ProgramPath()
		workdir = pp
		if len(sys.argv) > 1:
			workdir = sys.argv[1]
		config = getConfig(workdir,{'workdir':workdir,'ProgramPath':pp})
		if config.databases:
			DBPools(config.databases)
		initEnv()
		setupTemplateEngine()
		self.app = web.Application()
		auth = auth_klass()
		auth.setupAuth(self.app)
		self.configPath(config)

	def run(self):
		config = getConfig()
		ssl_context = None
		if config.website.ssl:
			ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
			ssl_context.load_cert_chain(config.website.ssl.crtfile,
						config.website.ssl.keyfile)
		web.run_app(self.app,host=config.website.host or '0.0.0.0',
							port=config.website.port or 8080,
							ssl_context=ssl_context)

	def configPath(self,config):
		for p,prefix in config.website.paths:
			res = ProcessorResource(prefix,p,show_index=True,
							follow_symlinks=True)
			res.setProcessors(config.website.processors or {})
			res.setIndexes(config.website.indexes or [])
			self.app.router.register_resource(res)
	
