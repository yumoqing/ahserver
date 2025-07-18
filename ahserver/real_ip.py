
from appPublic.log import exception, debug, error
from aiohttp import web

from aiohttp_middlewares.annotations import DictStrStr, Handler, Middleware

def real_ip_middleware() -> Middleware:
	@web.middleware
	async def middleware(
		request: web.Request, handler: Handler
	) -> web.StreamResponse:
		match_header_keys = [
			"X-Forwarded-For",
			"X-real-ip"
		]
		request['client_ip'] = request.remote
		for k,v in request.headers.items():
			if k in match_header_keys:
				v = v.split(',')[-1].strip()
				request['client_ip'] = v
				break
		return await handler(request)

	return middleware
