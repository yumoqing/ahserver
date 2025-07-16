import asyncio
import aiohttp
import aiofiles
import json
import codecs
from aiohttp import web
import aiohttp_cors
from traceback import print_exc
from appPublic.sshx import SSHNode
from appPublic.dictObject import DictObject
from appPublic.log import info, debug, warning, error, exception, critical
from .baseProcessor import BaseProcessor, PythonScriptProcessor

async def ws_send(ws:web.WebSocketResponse, data):
	info(f'data={data} {ws=}')
	d = {
		"type":1,
		"data":data
	}
	d = json.dumps(d, indent=4, ensure_ascii=False)
	try:
		return await ws.send_str(d)
	except Exception as e:
		exception(f'ws.send_str() error: {e=}')
		print_exc()
		return False

class WsSession:
	def __init__(self, session):
		self.session = session
		self.nodes = {}
	
	def join(node):
		self.nodes[node.id] = node
	
	def leave(node):
		self.nodes = {k:v for k,v in self.nodes.items() if k != node.id}
	
class WsData:
	def __init__(self):
		self.nodes = {}
		self.sessions = {}
	
	def add_node(self, node):
		self.nodes[node.id] = node
	
	def del_node(self, node):
		self.nodes = {k:v for k,v in self.nodes.items() if k!=node.id}
	
	def get_nodes(self):
		return self.nodes

	def get_node(self, id):
		return self.nodes.get(id)
	
	def add_session(self, session):
		self.sessions[session.sessionid] = session
	
	def del_session(self, session):
		self.sessions = {k:v for k,v in self.sessions.items() if k != session.sessionid}
	
	def get_session(self, id):
		return self.sessions.get(id)

class WsPool:
	def __init__(self, ws, ip, ws_path, app):
		self.app = app
		self.ip = ip
		self.id = None
		self.ws = ws
		self.ws_path = ws_path

	def get_data(self):
		r = self.app.get_data(self.ws_path)
		if r is None:
			r = WsData()
			self.set_data(r)
		return r

	def set_data(self, data):
		self.app.set_data(self.ws_path, data)

	def is_online(self, userid):
		data = self.get_data()
		node = data.get_node(userid)
		if node is None:
			return False
		return True

	def register(self, id):
		iddata = DictObject()
		iddata.id = id
		self.add_me(iddata)

	def add_me(self, iddata):
		data = self.get_data()
		iddata.ws = self.ws
		iddata.ip = self.ip
		self.id = iddata.id
		data.add_node(iddata)
		self.set_data(data)

	def delete_id(self, id):
		data = self.get_data()
		node = data.get_node(id)
		if node:
			data.del_node(node)
		self.set_data(data)

	def delete_me(self):
		self.delete_id(self.id)
		
	def add_session(self, session):
		data = self.get_data()
		data.add_session(session)
		self.set_data(data)
	
	def del_session(self, session):
		data = self.get_data()
		data.del_session(session)
		self.set_data(data)

	def get_session(self, sessionid):
		data = self.get_data()
		return data.get_session(sessionid)

	async def sendto(self, data, id=None):
		if id is None:
			return await ws_send(self.ws, data)
		d = self.get_data()
		iddata = d.get_node(id)
		ws = iddata.ws
		try:
			return await ws_send(ws, data)
		except:
			self.delete_id(id)

class WebsocketProcessor(PythonScriptProcessor):
	@classmethod
	def isMe(self,name):
		return name=='ws'

	async def path_call(self, request,params={}):
		cookie = request.headers.get('Sec-WebSocket-Protocol', None)
		if cookie:
			request.headers['Cookies'] = cookie
			userid = await get_user()
			debug(f'{cookie=}, {userid=}')
		await self.set_run_env(request)
		lenv = self.run_ns.copy()
		lenv.update(params)
		params_kw = lenv.params_kw
		userid = lenv.params_kw.userid or await lenv.get_user()
		del lenv['request']
		txt = await self.loadScript(self.real_path)
		ws = web.WebSocketResponse()
		try:
			await ws.prepare(request)
		except Exception as e:
			exception(f'--------except: {e}')
			print_exc()
			raise e
		ws_pool = WsPool(ws, request['client_ip'], request.path, request.app)
		debug(f'========== debug ===========')
		async for msg in ws:
			if msg.type == aiohttp.WSMsgType.TEXT:
				if msg.data == '_#_heartbeat_#_':
					await ws_send(ws, '_#_heartbeat_#_')
				else:
					lenv['ws_data'] = msg.data
					lenv['ws_pool'] = ws_pool
					exec(txt,lenv,lenv)
					func = lenv['myfunc']
					resp =  await func(request,**lenv)

			elif msg.type == aiohttp.WSMsgType.ERROR:
				error('ws connection closed with exception %s' % ws.exception())
				break
			else:
				info('datatype error', msg.type)
		debug(f'========== ws connection end ===========')
		ws_pool.delete_me()
		self.retResponse =  ws
		await ws.close()
		return ws

