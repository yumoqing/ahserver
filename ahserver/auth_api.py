from aiohttp_auth import auth
from os import urandom
from aiohttp import web
import aiohttp_session

from aiohttp_session import get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

class AuthAPI:
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
		app.router.add_route('POST','/login',self.login)
		app.router.add_route('GET', '/logout', self.logout)

	async def login(self,request):
		params = await request.post()
		user_id = params.get('user',None)
		password = params.get('password',None)
		from_path = params.get('from_path',None)
		if self.checkUserPassword(user_id,password):
			await auth.remember(request, user)
			return web.HpptFound(from_path)
		raise web.HTTPUnauthorized()

	async def logout(self,request):
		await auth.forget(request)
		return web.REsponse(body='OK'.encode('utf-8'))

	@web.middleware
	async def checkAuth(self,request,handler):
		path = request.path
		print(f'*****{path} checkAuth called********')
		if not await self.needAuth(path):
			return await handler(request)
		user = await auth.get_auth(request)
		if user is None:
			raise web.HTTPFound(f'/login_form?from_path={path}')
		user_perms = await self.getUserPermission(user)
		need_perm = await self.getPermissionNeed(path)
		if need_perm in user_perms:
			return await handler(request)
		print(f'**{path} forbidden**')
		raise web.HTTPForbidden()

	async def needAuth(self,path):
		return False

	async def getPermissionNeed(self,path):
		return 'admin'

	async def checkUserPassword(self,user_id,password):
		return True
	
	async def getUserPermissions(self,user):
		return ['admin','view']

