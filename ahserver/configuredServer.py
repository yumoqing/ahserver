import os,sys
import time
import ssl
from socket import *
from aiohttp import web

from appPublic.folderUtils import ProgramPath
from appPublic.background import Background
from appPublic.jsonConfig import getConfig
from appPublic.i18n import getI18N

from sqlor.dbpools import DBPools

from .processorResource import ProcessorResource
from .auth_api import AuthAPI
from .myTE import setupTemplateEngine
from .globalEnv import initEnv
try:
	from natpmp import NATPMP as pmp
except:
	pmp = None

class ConfiguredServer:
	def __init__(self, auth_klass=AuthAPI, workdir=None):
		pp = ProgramPath()
		if workdir is None:
			self.natpmp_loop = True
			self.nat_heartbeat = False
			workdir = pp
			if len(sys.argv) > 1:
				workdir = sys.argv[1]
		config = getConfig(workdir,{'workdir':workdir,'ProgramPath':pp})
		i18n = getI18N(path=workdir)
		if config.databases:
			DBPools(config.databases)
		initEnv()
		setupTemplateEngine()
		self.app = web.Application()
		auth = auth_klass()
		auth.setupAuth(self.app)
		self.configPath(config)

	def natpmp_heartbeat(self):
		config = getConfig()
		udpCliSock = socket(AF_INET,SOCK_DGRAM)
		msg = f'{config.natpmp.appname}:{config.natpmp.nodename}'.encode('utf-8')
		t = config.natpmp.heartbeat_period or 60
		addr = (gethostbyname(config.natpmp.natserver), config.natpmp.natport)
		while self.nat_heartbeat:
			udpCliSock.sendto(msg, addr)
			udpCliSock.recv(1024)
			time.sleep(t)

	def nat_pmp(self):
		config = getConfig()
		t = config.natpmp.portmap_period or 3600
		while self.natpmp_loop:
			gateway = pmp.get_gateway_addr()
			print('gateway=', gateway)
			try:
				x = pmp.map_port(pmp.NATPMP_PROTOCOL_TCP, 
								config.natpmp.public_port, config.website.port, 
								t, gateway_ip=gateway)
				print('gateway=', gateway, 'map_port()=', x)
			except Exception as e:
				print('mat_pmp():Exception:',e)
			time.sleep(t - 1)
			

			
	def run(self):
		config = getConfig()
		ssl_context = None
		if config.website.ssl:
			ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
			ssl_context.load_cert_chain(config.website.ssl.crtfile,
						config.website.ssl.keyfile)
		if pmp and config.natpmp:
			self.nat_heartbeat = True
			b = Background(self.natpmp_heartbeat)
			b.start()

		if not config.natpmp:
			self.natpmp_loop = False
		elif config.natpmp.hardmap:
			self.natpmp_loop = False
		else:
			b = Background(self.nat_pmp)
			b.start()
		web.run_app(self.app,host=config.website.host or '0.0.0.0',
							port=config.website.port or 8080,
							ssl_context=ssl_context)

	def configPath(self,config):
		for p,prefix in config.website.paths:
			res = ProcessorResource(prefix,p,show_index=True,
							follow_symlinks=True,
							indexes=config.website.indexes,
							processors=config.website.processors)
			self.app.router.register_resource(res)
	
