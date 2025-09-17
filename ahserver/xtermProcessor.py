from traceback import format_exc
import asyncio
import aiohttp
import aiofiles
import json
import codecs
from aiohttp import web
import aiohttp_cors
from appPublic.sshx import SSHServer
from appPublic.dictObject import DictObject
from appPublic.log import info, debug, warning, error, exception, critical
from .baseProcessor import BaseProcessor, PythonScriptProcessor

class ResizeException(Exception):
	def __init__(self, rows, cols):
		self.rows = rows
		self.cols = cols

class XtermProcessor(PythonScriptProcessor):
	@classmethod
	def isMe(self,name):
		return name=='xterm'

	async def ws_2_process(self, ws):
		async for msg in ws:
			if msg.type == aiohttp.WSMsgType.TEXT:
				data = DictObject(**json.loads(msg.data))
				if data.type == 'close':
					debug(f'accept client close request, close the ws')
					self.running = False
					return
				if data.type == 'input':
					self.p_obj.stdin.write(data.data)
				elif data.type == 'heartbeat':
					await self.ws_send_heartbeat(ws)
				elif data.type == 'resize':
					try:
						self.p_obj._chan.change_terminal_size(data.cols, data.rows)
					except Exception as e:
						exception(f'{data=}, {e=}, {format_exc()}')
						
			elif msg.type == aiohttp.WSMsgType.ERROR:
				debug(f'ws connection closed with exception {ws.exception()}')
				return
			else:
				debug('recv from ws:{msg}+++++++++++')
			await asyncio.sleep(0)
		
	async def process_2_ws(self, ws):
		try:
			while self.running:
				x = await self.p_obj.stdout.read(1024)
				await self.ws_send_data(ws, x)
				await asyncio.sleep(0)
		finally:
			self.p_obj.close()

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

		# debug(f'{login_info=}')
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
			self.p_obj = await conn.create_process(term_type='xterm-256color', term_size=(80, 24))
			r1 = self.ws_2_process(ws)
			r2 = self.process_2_ws(ws)
			await asyncio.gather(r1,r2)
		debug(f'run_xterm() ended')

	async def ws_send_heartbeat(self, ws):
		dic = {
			'type':'heartbeat'
		}
		await self.ws_send(ws, dic)

	async def ws_send_data(self, ws, d):
		dic = {
			'type':'data',
			'data':d
		}
		await self.ws_send(ws, dic)

	async def ws_send(self, ws:web.WebSocketResponse, s):
		data = {
			"type":1,
			"data":s
		}
		await ws.send_str(json.dumps(data, indent=4, ensure_ascii=False))


