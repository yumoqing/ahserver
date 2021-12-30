
import os
import codecs
from aiohttp.web_exceptions import (
HTTPException
)
import ujson as json
from .baseProcessor import BaseProcessor
from crud_engine.crud_engine import CRUDEngine

class CrudProcessor(BaseProcessor):
	@classmethod
	def isMe(self, name):
		return name == 'crud'

	def get_default_filter_data(self):
		subffix = '.filterdata'
		user = self.run_evn.get('user')
		if user:
			subffix = f'{subffix}.{user}'
		f = f'{self.real_path}{subffix}'
		if os.path.exists(f):
			with codecs.open(f, 'r', 'utf-8') as ff:
				d = json.load(ff)
				return d
		return None
		
	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		dic = {}
		with codecs.open(self.real_path, 'r', 'utf-8') as f:
			dic = json.load(f)
		x = request.path.split('/')
		if len(x) >= 2:
			act = x[-2]
			if not CRUDEngine.is_legal_cmd(act):
				act = CRUDEngine.defaultcmd()
			default_filter_data = self.get_default_filter_data()
			ce = CRUDEngine(self.resource, dic, default_filter_data)
			return await ce.dispatch(act)
		raise HttpException(555)

	async def datahandle(self, request):
		self.content =  await self.path_call(request)

