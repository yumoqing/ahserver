
from appPublic.dictObject import DictObject
from appPublic.registerfunction import RegisterFunction

from aiohttp.web_response import Response, StreamResponse
from .baseProcessor import BaseProcessor

class FunctionProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return False

	def __init__(self,path,resource, opts):
		self.config_opts = opts
		BaseProcessor.__init__(self,path,resource)

	async def datahandle(self,request):
		ns = self.config_opts.copy()
		ns.update(self.run_ns)
		ns = DictObject(**ns)
		rf = RegisterFunction()
		f = rf.get(ns.registerfunction)
		x = await f(ns)
		if isinstance(x,Response):
			self.retResponse = x
		else:
			self.content = x

