from aiohttp_auth import auth
from os import urandom
from aiohttp import web
import aiohttp_session

from aiohttp_session import get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from appPublic.jsonConfig import getConfig
from appPublic.rsa import RSA
class AuthAPI:

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
		policy = auth.SessionTktAuthentication(urandom(32), 60,
											   include_ip=True)

		# setup aiohttp_auth.auth middleware in aiohttp fashion
		auth.setup(app, policy)
		app.middlewares.append(self.checkAuth)
		app.router.add_route('GET', '/logout', self.logout)

	async def checkLogin(self,request):
		"""
		authorization header has the format:
		login_method:user_id:auth_code
		"""
		authinfo = request.headers.get('authorization')
		if authinfo is None:
			print('header not include "authorization" info', request.headers)
			raise web.HTTPUnauthorized()
			
		authdata = self.rsaDecode(authinfo)
		# print('authdata=',authdata)
		alist = authdata.split('::')
		if len(alist) != 3:
			print('auth data format error')
			raise web.HTTPUnauthorized()

		login_method=alist[0]
		user_id = alist[1]
		password = alist[2]
		if login_method == 'password':
			if await self.checkUserPassword(user_id,password):
				await auth.remember(request,user_id)
				# print('auth success,',user_id, password)
				return user_id
			# print('auth failed')
			raise web.HTTPUnauthorized()
		else:
			# print('auth method unrecognized------------------------')
			raise web.HTTPUnauthorized()

	async def logout(self,request):
		await auth.forget(request)
		return web.Response(body='OK'.encode('utf-8'))

	@web.middleware
	async def checkAuth(self,request,handler):
		path = request.path
		# print(f'*****{path} checkAuth called********')
		if not await self.needAuth(path):
			return await handler(request)
		user = await auth.get_auth(request)
		if user is None:
			# print('-----------auth.get_auth() return None--------------')
			user = await self.checkLogin(request)
			#raise web.HTTPFound(f'/login_form?from_path={path}')
		user_perms = await self.getUserPermissions(user)
		need_perm = await self.getPermissionNeed(path)
		if need_perm in user_perms:
			return await handler(request)
		# print(f'**{path} forbidden**')
		raise web.HTTPForbidden()

	async def needAuth(self,path):
		return False

	async def getPermissionNeed(self,path):
		return 'admin'

	async def checkUserPassword(self,user_id,password):
		return True
	
	async def getUserPermissions(self,user):
		return ['admin','view']

