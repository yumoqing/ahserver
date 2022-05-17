import os
import re
import json
import codecs
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse

from appPublic.jsonConfig import getConfig
from appPublic.dictObject import DictObject
from appPublic.folderUtils import listFile

from .utils import unicode_escape
from .serverenv import ServerEnv

class ObjectCache:
	def __init__(self):
		self.cache = {}

	def store(self,path,obj):
		o = self.cache.get(path,None)
		if o is not None:
			try:
				del o.cached_obj
			except:
				pass
		o = DictObject()
		o.cached_obj = obj
		o.mtime = os.path.getmtime(path)
		self.cache[path] = o

	def get(self,path):
		o = self.cache.get(path)
		if o:
			if os.path.getmtime(path) > o.mtime:
				return None
			return o.cached_obj
		return None


		
class BaseProcessor:
	@classmethod
	def isMe(self,name):
		return name=='base'

	def __init__(self,path,resource):
		self.path = path
		self.resource = resource
		self.retResponse = None
		# self.last_modified = os.path.getmtime(path)
		# self.content_length = os.path.getsize(path)
		self.headers = {
			'Content-Type': 'text/html; utf-8',
			'Accept-Ranges': 'bytes'
		}
		self.content = ''

	async def set_run_env(self, request):
		self.real_path = self.resource.url2file(self.resource.entireUrl(request, self.path))
		g = ServerEnv()
		self.run_ns = {}
		self.run_ns.update(g)
		self.run_ns.update(self.resource.y_env)
		self.run_ns['request'] = request
		kw = await self.run_ns['request2ns']()
		self.run_ns['params_kw'] = kw
		self.run_ns.update(kw)
		self.run_ns['ref_real_path'] = self.real_path
		self.run_ns['processor'] = self

	async def execute(self,request):
		await self.set_run_env(request)
		await self.datahandle(request)
		return self.content

	async def handle(self,request):
		await self.execute(request)
		if self.retResponse is not None:
			return self.retResponse
		elif type(self.content) == type({}) :
			self.content = json.dumps(self.content,
				indent=4)
		elif  isinstance(self.content,DictObject):
			mydict = self.content.to_dict()
			self.content = json.dumps(mydict, indent=4)
		elif type(self.content) == type([]):
			self.content = json.dumps(self.content,
				indent=4)
		
		self.headers['Content-Type'] = "application/json; utf-8"
		return Response(text=self.content,headers=self.headers)

	async def datahandle(self,request):
		print('*******Error*************')
		self.content=''

	def setheaders(self):
		pass
		# self.headers['Content-Length'] = str(len(self.content))

class TemplateProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='tmpl'

	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		path = self.path
		url = self.resource.entireUrl(request, path)
		ns = self.run_ns
		ns.update(params)
		te = self.run_ns['tmpl_engine']
		return await te.render(url,**ns)

	async def datahandle(self,request):
		self.content = await self.path_call(request)
		
	def setheaders(self):
		super(TemplateProcessor,self).setheaders()
		if self.path.endswith('.tmpl.css'):
			self.headers['Content-Type'] = 'text/css; utf-8'
		elif self.path.endswith('.tmpl.js'):
			self.headers['Content-Type'] = 'application/javascript ; utf-8'
		else:
			self.headers['Content-Type'] = 'text/html; utf-8'

class JSUIProcessor(TemplateProcessor):
	@classmethod
	def isMe(self,name):
		return name=='jsui'

	async def datahandle(self, request):
		params = await self.resource.y_env['request2ns']()
		if params.get('_jsui',None):
			super().datahandle(request)
		else:
			content0 = await self.resource.path_call(request,'/header.tmpl')
			content1 = await self.resource.path_call(request,self.path)
			content2 = await self.resource.path_call(request,'/footer.tmpl')
			self.content = '%s%s%s' % (content0,content1,content2)

class PythonScriptProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='dspy'

	def loadScript(self, path):
		data = ''
		with codecs.open(path,'rb','utf-8') as f:
			data = f.read()
		b= ''.join(data.split('\r'))
		lines = b.split('\n')
		lines = ['\t' + l for l in lines ]
		txt = "async def myfunc(request,**ns):\n" + '\n'.join(lines)
		return txt
		
	async def path_call(self, request,params={}):
		await self.set_run_env(request)
		lenv = self.run_ns
		lenv.update(params)
		del lenv['request']
		txt = self.loadScript(self.real_path)
		exec(txt,lenv,lenv)
		func = lenv['myfunc']
		return await func(request,**lenv)

	async def datahandle(self,request):
		self.content = await self.path_call(request)

class MarkdownProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='md'

	async def datahandle(self,request:Request):
		data = ''
		with codecs.open(self.real_path,'rb','utf-8') as f:
			data = f.read()
			self.content = self.urlreplace(data, request)

	def urlreplace(self,mdtxt,request):
		p = '\[(.*)\]\((.*)\)'
		return re.sub(p,
				lambda x:'['+x.group(1)+'](' + self.resource.entireUrl(request, x.group(2)) + ')',
				mdtxt)

def getProcessor(name):
	return _getProcessor(BaseProcessor,name)
	
def _getProcessor(kclass,name):
	for k in kclass.__subclasses__():
		if not hasattr(k,'isMe'):
			continue
		if k.isMe(name):
			return k
		a = _getProcessor(k,name)
		if a is not None:
			return a
	return None
