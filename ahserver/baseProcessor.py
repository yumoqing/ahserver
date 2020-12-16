import os
import re
import json
import codecs
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse

from jinja2 import Template,Environment,BaseLoader

from appPublic.jsonConfig import getConfig
from appPublic.dictObject import DictObject
from appPublic.folderUtils import listFile

from .serverenv import ServerEnv

def unicode_escape(s):
	x = [ch if ord(ch) < 256 else ch.encode('unicode_escape').decode('utf-8') for ch in s]
	return ''.join(x)

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

	
	async def execute(self,request):
		g = ServerEnv()
		self.run_ns = {}
		self.run_ns.update(g)
		self.run_ns.update(self.resource.y_env)
		self.run_ns['request'] = request
		self.run_ns['params_kw'] = await self.run_ns['request2ns']()
		self.run_ns['ref_real_path'] = self.path
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
			print('mydict=',mydict,type(mydict))
			self.content = json.dumps(mydict, indent=4)
		elif type(self.content) == type([]):
			self.content = json.dumps(self.content,
				indent=4)
		self.content = unicode_escape(self.content)
		self.setheaders()
		return Response(text=self.content,headers=self.headers)

	async def datahandle(self,request):
		print('*******Error*************')
		self.content=''

	def setheaders(self):
		self.headers['Content-Length'] = str(len(self.content))

class TemplateProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='tmpl'

	async def datahandle(self,request):
		path = request.path
		ns = self.run_ns
		te = self.run_ns['tmpl_engine']
		self.content = te.render(path,**ns)
		
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

	async def path_call(self, request, path):
		ns = self.run_ns
		te = self.run_ns['tmpl_engine']
		return te.render(path,**ns)
		

	async def datahandle(self, request):
		params = await self.resource.y_env['request2ns']()
		if params.get('_jsui',None):
			super().datahandle(request)
		else:
			content0 = await self.path_call(request,'/header.tmpl')
			content1 = await self.path_call(request,self.path)
			content2 = await self.path_call(request,'/footer.tmpl')
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
		
	async def path_call(self, request, path):
		g = ServerEnv()
		lenv = self.run_ns
		del lenv['request']
		txt = self.loadScript(path)
		exec(txt,lenv,lenv)
		func = lenv['myfunc']
		return await func(request,**lenv)

	async def datahandle(self,request):
		self.content = await self.path_call(request, self.path)

class MarkdownProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='md'

	async def datahandle(self,request:Request):
		data = ''
		with codecs.open(self.path,'rb','utf-8') as f:
			data = f.read()
		b = data
		b = self.urlreplace(b,request)
		ret = {
				"__widget__":"markdown",
				"data":{
					"md_text":b
				}
		}
		config = getConfig()
		self.content = json.dumps(ret,indent=4)

	def urlreplace(self,mdtxt,request):
		def replaceURL(s):
			p1 = '\[.*?\]\((.*?)\)'
			url = re.findall(p1,s)[0]
			txts = s.split(url)
			url = self.resource.absUrl(request,url)
			return url.join(txts)

		p = '\[.*?\]\(.*?\)'
		textarray = re.split(p,mdtxt)
		links = re.findall(p,mdtxt)
		newlinks = [ replaceURL(link) for link in links]
		if len(links)>0:
			mdtxt = ''
			for i in range(len(newlinks)):
				mdtxt = mdtxt + textarray[i]
				mdtxt = mdtxt + newlinks[i]
			mdtxt = mdtxt + textarray[i+1]
		return mdtxt

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
