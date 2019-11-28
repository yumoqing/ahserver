
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

	async def datahandle(self,request):
		ns = self.config_opts.options.copy()
		ns.update(self.run_ns)
		ns = DictObject(ns)
		fname = self.config_opts.registerfunction
		rf = RegisterFunction()
		f = rf.get(fname)
		x = await f(ns)
		if isinstance(x,Response):
			self.retResponse = x
		else:
			self.content = x

