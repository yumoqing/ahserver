import asyncio
import aiohttp
import json
import codecs
from aiohttp import web
import aiohttp_cors
from appPublic.sshx import SSHNode
from .baseProcessor import BaseProcessor, PythonScriptProcessor

class XtermProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='xterm'

	async def ws_2_process(self, ws):
		async for msg in ws:
			if msg.type == aiohttp.WSMsgType.TEXT:
				self.p_obj.stdin.write(msg.data)
			elif msg.type == aiohttp.WSMsgType.ERROR:
				print('ws connection closed with exception %s' % ws.exception())
				return
		
	async def process_2_ws(self, ws):
		while self.running:
			x = await self.p_obj.stdout.read(1024)
			await self.ws_sendstr(ws, x)

	async def datahandle(self,request):
		await self.path_call(request)
		
	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		lenv = self.run_ns.copy()
		lenv.update(params)
		del lenv['request']
		ws = web.WebSocketResponse()
		await ws.prepare(request)
		await self.create_process()
		self.ws_sendstr(ws, 'Welcom to sshclient')
		r1 = self.ws_2_process(ws)
		r2 = self.process_2_ws(ws)
		await asyncio.gather(r1,r2)
		self.retResponse = ws
		return ws

	def get_login_info(self):
		with codecs.open(self.real_path, 'r', 'utf-8') as f:
			self.login_info = json.load(f)
		print(f'{self.login_info=}')

	async def create_process(self):
		# id = lenv['params_kw'].get('termid')
		self.get_login_info()
		host = self.login_info['host']
		port = self.login_info.get('port', 22)
		username = self.login_info.get('username', 'root')
		password = self.login_info.get('password',None)
		self.sshnode = SSHNode(host, username=username,
									password=password,
									port=port)
		await self.sshnode.connect()
		self.p_obj = await self.sshnode._process('bash',
											term_type='vt100',
											term_size=(80, 24),
											encoding='utf-8')
		self.running = True

	async def ws_sendstr(self, ws:web.WebSocketResponse, s:str):
		data = {
			"type":1,
			"data":s
		}
		await ws.send_str(json.dumps(data))

	def close_process(self):
		self.sshnode.close()
		self.p_obj.close()

class WebsocketProcessor(PythonScriptProcessor):
	@classmethod
	def isMe(self,name):
		return name=='ws'

	async def ws_sendstr(self, ws:web.WebSocketResponse, s:str):
		data = {
			"type":1,
			"data":s
		}
		await ws.send_str(json.dumps(data))

	async def path_call(self, request,params={}):
		print('1----------------------------------')
		await self.set_run_env(request)
		lenv = self.run_ns.copy()
		lenv.update(params)
		del lenv['request']
		print('2----------------------------------')
		txt = self.loadScript(self.real_path)
		exec(txt,lenv,lenv)
		func = lenv['myfunc']
		print('3----------------------------------')
		ws = web.WebSocketResponse()
		await ws.prepare(request)
		print('4----------------------------------', aiohttp.WSMsgType.TEXT)
		await self.ws_sendstr(ws, 'Welcome to websock')
		async for msg in ws:
			if msg.type == aiohttp.WSMsgType.TEXT:
				print('msg=:', msg)
				lenv['ws_data'] = msg.data
				# resp =  await func(request,**lenv)
				await self.ws_sendstr(ws, msg.data)
				print('msg.data=', msg.data)
			elif msg.type == aiohttp.WSMsgType.ERROR:
				print('ws connection closed with exception %s' % ws.exception())
			else:
				print('datatype error', msg.type)
		print('5----------------------------------')
		self.retResponse =  ws
		await ws.close()
		return ws

