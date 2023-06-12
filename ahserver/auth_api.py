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

	def getPrivateKey(self):
		if not hasattr(self,'rsaEngine'):
			self.rsaEngine = RSA()
			self.conf = getConfig()
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
		policy = auth.SessionTktAuthentication(urandom(32), 3600,
											   include_ip=True)

		# setup aiohttp_auth.auth middleware in aiohttp fashion
		# print('policy = ', policy)
		auth.setup(app, policy)
		app.middlewares.append(self.checkAuth)
		app.router.add_route('GET', '/logout', self.logout)

	async def logout(self,request):
		await auth.forget(request)
		return web.Response(body='OK'.encode('utf-8'))

	@web.middleware
	async def checkAuth(self,request,handler):
		path = request.path
		if not await self.needAuth(path):
			return await handler(request)
		user = await auth.get_auth(request)
		is_ok = await self.checkUserPermission(user, path)
		if is_ok:
			return await handler(request)
		# print(f'**{path} forbidden**')
		raise web.HTTPForbidden()

	async def checkUserPermission(user, path):
		return True

	async def needAuth(self,path):
		return False

