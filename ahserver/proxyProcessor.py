from aiohttp import web
from aiohttp import client
from .baseProcessor import *

class ProxyProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='proxy'

	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		path = self.path
		url = self.resource.entireUrl(request, path)
		ns = self.run_ns
		ns.update(params)
		te = self.run_ns['tmpl_engine']
		txt = await te.render(url,**ns)
		data = json.loads(txt)
		print('proxyProcessor: data=', data)
		return data

	async def datahandle(self,request):
		d  = await self.path_call(request)
		reqH = request.headers.copy()
		async with client.request(
				request.method,
				d['url'],
				headers = reqH,
				allow_redirects=False,
				data=await req.read()) as res:
			headers = res.headers.copy()
			body = await res.read()
			self.retResponse = web.Response(
					headers = headers,
					status = res.status,
					body = body
			)
			print('proxy: datahandle() finish', self.retResponse)

		
	def setheaders(self):
		pass

