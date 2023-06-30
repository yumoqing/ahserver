from aiohttp_auth import auth
from os import urandom
from aiohttp import web
import aiohttp_session
import base64

from aiohttp_session import get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from appPublic.jsonConfig import getConfig
from appPublic.rsawrap import RSA
from appPublic.app_logger import AppLogger
class AuthAPI(AppLogger):
	def __init__(self):
		super().__init__()
		self.conf = getConfig()

	def getPrivateKey(self):
		if not hasattr(self,'rsaEngine'):
			self.rsaEngine = RSA()
			fname = self.conf.website.rsakey.privatekey
			self.privatekey = self.rsaEngine.read_privatekey(fname)
		return self.privatekey

	def rsaDecode(self,cdata):
		self.getPrivateKey()
		return self.rsaEngine.decode(self.privatekey,cdata)

	def setupAuth(self,app):
		# setup session middleware in aiohttp fashion
		storage = EncryptedCookieStorage(urandom(32))
		aiohttp_session.setup(app, storage)

		# Create an auth ticket mechanism that expires after 1 minute (60
		# seconds), and has a randomly generated secret. Also includes the
		# optional inclusion of the users IP address in the hash
		session_max_time = 120
		session_reissue_time = 30
		if self.conf.website.session_max_time:
			session_max_time = self.conf.website.session_max_time
		if self.conf.website.session_reissue_time:
			session_reissue_time = self.conf.website.session_reissue_time
		
		policy = auth.SessionTktAuthentication(urandom(32), session_max_time,
												reissue_time=session_reissue_time,
											   include_ip=True)

		# setup aiohttp_auth.auth middleware in aiohttp fashion
		# print('policy = ', policy)
		auth.setup(app, policy)
		print('add auth middleware ....................')
		app.middlewares.append(self.checkAuth)

	@web.middleware
	async def checkAuth(self,request,handler):
		path = request.path
		user = await auth.get_auth(request)
		is_ok = await self.checkUserPermission(user, path)
		if is_ok:
			return await handler(request)
		if user is None:
			print(f'**{user=}, {path} need login**')
			raise web.HTTPUnauthorized
		print(f'**{user=}, {path} forbidden**')
		raise web.HTTPForbidden()

	async def checkUserPermission(self, user, path):
		raise Exception('checkUserPermission()')
		return False

	async def needAuth(self,path):
		return False

