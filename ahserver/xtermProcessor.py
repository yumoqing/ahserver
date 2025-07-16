import asyncio
import aiohttp
import aiofiles
import json
import codecs
from aiohttp import web
import aiohttp_cors
from traceback import print_exc
from appPublic.sshx import SSHServer
from appPublic.dictObject import DictObject
from appPublic.log import info, debug, warning, error, exception, critical
from .baseProcessor import BaseProcessor, PythonScriptProcessor

class XtermProcessor(PythonScriptProcessor):
	@classmethod
	def isMe(self,name):
		return name=='xterm'

	async def ws_2_process(self, ws):
		async for msg in ws:
			if msg.type == aiohttp.WSMsgType.TEXT:
				debug(f'recv from ws:{msg}')
				resize_pattern = '_#_resize_#_'
				heartbeat_pattern = '_#_heartbeat_#_'
				if msg.data.startswith(resize_pattern):
					row, col = [ int(i) for i in msg.data[len(resize_pattern):].split(',')]
					await self.p_obj.set_terminal_size(row, col)
					continue
				if msg.data == heartbeat_pattern:
					await self.ws_sendstr(ws, heartbeat_pattern)
					continue
				self.p_obj.stdin.write(msg.data)
			elif msg.type == aiohttp.WSMsgType.ERROR:
				# print('ws connection closed with exception %s' % ws.exception())
				return
		
	async def process_2_ws(self, ws):
		while self.running:
			x = await self.p_obj.stdout.read(1024)
			await self.ws_sendstr(ws, x)
			await asyncio.sleep(0)

	async def datahandle(self,request):
		await self.path_call(request)
		
	async def path_call(self, request, params={}):
		#
		# xterm file is a python script as dspy file
		# it must return a DictObject with sshnode information
		# parameters: nodeid
		#
		await self.set_run_env(request, params=params)
		login_info = await super().path_call(request, params=params)
		if login_info is None:
			raise Exception('data error')

		debug(f'{login_info=}')
		ws = web.WebSocketResponse()
		await ws.prepare(request)
		await self.run_xterm(ws, login_info)
		self.retResponse = ws
		return ws

	async def run_xterm(self, ws, login_info):
		# id = lenv['params_kw'].get('termid')
		self.sshnode = SSHServer(login_info)
		async with self.sshnode.get_connector() as conn:
			self.running = True
			self.p_obj = await conn.create_process(term_type='xterm', term_size=(24, 80))
			stdin_task = asyncio.create_task(self.ws_2_process(ws))
			try:
				while self.running:
					x = await self.p_obj.stdout.read(1024)
					await self.ws_sendstr(ws, x)
			except (asyncio.CancelledError, EOFError):
				pass
			finally:
				self.p_obj.close()
				stdin_task.cancel()

	async def ws_sendstr(self, ws:web.WebSocketResponse, s:str):
		data = {
			"type":1,
			"data":s
		}
		debug(f'{data=}')
		await ws.send_str(json.dumps(data, indent=4, ensure_ascii=False))
		debug(f'{data=} sended')


