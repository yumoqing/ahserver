
import inspect
from appPublic.dictObject import DictObject
from appPublic.registerfunction import RegisterFunction
from appPublic.log import info, debug, warning, error, exception, critical
from aiohttp import web
from aiohttp.web_response import Response, StreamResponse
from .baseProcessor import BaseProcessor

class FunctionProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return False

	def __init__(self,path,resource, opts):
		self.config_opts = opts
		BaseProcessor.__init__(self,path,resource)

	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		params_kw = self.run_ns.get('params_kw')
		path = params.get('path', request.path)
		path1 = path[len(self.config_opts['leading']):]
		args = []
		if len(path1) > 0:
			if path1[0] == '/':
				path1 = path1[1:]
			args += path1.split('/')

		
		rfname = self.config_opts['registerfunction']
		ns = DictObject(**self.run_ns)
		rf = RegisterFunction()
		f = rf.get(rfname)
		if f is None:
			error(f'{rfname=} is not registered, {rf.registKW=}')
			return None
		# self.run_ns['request'] = request
		# globals().update(self.run_ns)
		
		env = {k:v for k,v in self.run_ns.items() if k not in ['params_kw', 'request'] }
		if inspect.iscoroutinefunction(f):
			return await f(request, params_kw, *args, **env)
		return f(request, params_kw, *args, **env)

	async def datahandle(self,request):
		x = await self.path_call(request)
		if isinstance(x,web.FileResponse):
			self.retResponse = x
		elif isinstance(x,Response):
			self.retResponse = x
		else:
			self.content = x

