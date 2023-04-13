import aiohttp
from aiohttp import web
from .baseProcessor import PythonScriptProcessor

class WebSocketProcessor(PythonScriptProcessor):
	@classmethod
	def isMe(self,name):
		return name=='ws'

	async def path_call(self, request,params={}):
		await self.set_run_env(request)
		lenv = self.run_ns.copy()
		lenv.update(params)
		del lenv['request']
		txt = self.loadScript(self.real_path)
		exec(txt,lenv,lenv)
		func = lenv['myfunc']
		ws = web.WebSocketResponse()
		await ws.prepare(request)
		async for msg in ws:
			if msg.type == aiohttp/WSMsgType.TEXT:
				if msg.data == 'close':
					await ws.close()
				else:
					lenv['ws_data'] = msg.data
					resp =  await func(request,**lenv)
					await ws.send_str(resp)
			elif msg.type == aiohttp.WSMsgType.ERROR:
				print('ws connection closed with exception %s' % ws.exception())
		return ws

