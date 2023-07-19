import time
from aiohttp_auth import auth
from aiohttp_auth.auth.ticket_auth import TktAuthentication
from os import urandom
from aiohttp import web
import aiohttp_session
import aioredis
import base64

from aiohttp_session import get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session.redis_storage import RedisStorage

from appPublic.jsonConfig import getConfig
from appPublic.rsawrap import RSA
from appPublic.app_logger import AppLogger

class AuthAPI(AppLogger):
	def __init__(self):
		super().__init__()
		self.conf = getConfig()

	async def checkUserPermission(self, user, path):
		print('************* checkUserPermission() use default one ****************')
		return True

	def getPrivateKey(self):
		if not hasattr(self,'rsaEngine'):
			self.rsaEngine = RSA()
			fname = self.conf.website.rsakey.privatekey
			self.privatekey = self.rsaEngine.read_privatekey(fname)
		return self.privatekey

	def rsaDecode(self,cdata):
		self.getPrivateKey()
		return self.rsaEngine.decode(self.privatekey,cdata)

	async def setupAuth(self,app):
		# setup session middleware in aiohttp fashion
			
		storage = EncryptedCookieStorage(urandom(32))
		if self.conf.website.session_redis:
			url = self.conf.website.session_redis.url
			# redis = await aioredis.from_url("redis://127.0.0.1:6379")
			redis = await aioredis.from_url(url)
			storage = aiohttp_session.redis_storage.RedisStorage(redis)
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
		
		def _get_ip(self,request):
			ip = request.headers.get('X-Forwarded-For')
			if not ip:
				ip = request.remote
			return ip

		def _new_ticket(self, request, user_id):
			client_uuid = request.headers.get('client_uuid')
			ip = self._get_ip(request)
			if not ip:
				ip = request.remote
			valid_until = int(time.time()) + self._max_age
			print(f'hack: my _new_ticket() called ...remote {ip=}, {client_uuid=}')
			return self._ticket.new(user_id, valid_until=valid_until, client_ip=ip, user_data=client_uuid)

		TktAuthentication._get_ip = _get_ip
		TktAuthentication._new_ticket = _new_ticket
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
		print('checkAuth() called ..................')
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

	async def needAuth(self,path):
		return False

