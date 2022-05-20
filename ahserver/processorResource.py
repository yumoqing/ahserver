import os
import re
import codecs
from traceback import print_exc

import asyncio

from yarl import URL

from appPublic.http_client import Http_Client
from functools import partial
from aiohttp_auth import auth
from aiohttp.web_urldispatcher import StaticResource, _WebHandler, PathLike
from aiohttp.web_urldispatcher import Optional, _ExpectHandler
from aiohttp.web_urldispatcher import Path
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_exceptions import (
	HTTPException,
	HTTPExpectationFailed,
	HTTPForbidden,
	HTTPMethodNotAllowed,
	HTTPNotFound,
)
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_routedef import AbstractRouteDef

from appPublic.jsonConfig import getConfig
from appPublic.i18n import getI18N
from appPublic.dictObject import DictObject, multiDict2Dict
from appPublic.timecost import TimeCost
from appPublic.timeUtils import timestampstr

from .baseProcessor import getProcessor
from .xlsxdsProcessor import XLSXDataSourceProcessor
from .sqldsProcessor import SQLDataSourceProcessor
from .functionProcessor import FunctionProcessor
from .proxyProcessor import ProxyProcessor
from .serverenv import ServerEnv
from .url2file import Url2File
from .filestorage import FileStorage
from .restful import DBCrud
from .dbadmin import DBAdmin
from .filedownload import file_download, path_decode
from .utils import unicode_escape

def getHeaderLang(request):
	al = request.headers.get('Accept-Language')
	if al is None:
		return 'en'
	return al.split(',')[0]
	
def i18nDICT(request):
	c = getConfig()
	i18n = getI18N()
	lang = getHeaderLang(request)
	l = c.langMapping.get(lang,lang)
	return json.dumps(i18n.getLangDict(l)).encode(c.website.coding)


class ProcessorResource(StaticResource,Url2File):
	def __init__(self, prefix: str, directory: PathLike,
				 *, name: Optional[str]=None,
				 expect_handler: Optional[_ExpectHandler]=None,
				 chunk_size: int=256 * 1024,
				 show_index: bool=False, follow_symlinks: bool=False,
				 append_version: bool=False,
				 indexes:list=[],
				 processors:dict={}) -> None:
		StaticResource.__init__(self,prefix, directory,
				 name=name,
				 expect_handler=expect_handler,
				 chunk_size=chunk_size,
				 show_index=show_index, 
				 follow_symlinks=follow_symlinks,
				 append_version=append_version)
		Url2File.__init__(self,directory,prefix,indexes,inherit=True)
		gr = self._routes.get('GET')
		self._routes.update({'POST':gr})
		self._routes.update({'PUT':gr})
		self._routes.update({'OPTIONS':gr})
		self._routes.update({'DELETE':gr})
		self._routes.update({'TRACE':gr})
		self.y_processors = processors
		self.y_prefix = prefix
		self.y_directory = directory
		self.y_indexes = indexes
		self.y_env = DictObject()
		
	def setProcessors(self, processors):
		self.y_processors = processors

	def setIndexes(self, indexes):
		self.y_indexes = indexes

	def abspath(self, request, path:str):
		url =  self.entireUrl(request, path)
		return self.url2file(url)

	async def getPostData(self,request: Request) -> dict:
		reader = await request.multipart()
		if reader is None:
			md = await request.post()
			ns = multiDict2Dict(md)
			return ns
		ns = {}
		while 1:
			field = await reader.next()
			if not field:
				break
			value = ''
			if hasattr(field,'filename'):
				saver = FileStorage()
				value = await saver.save(field.filename,field.read_chunk)
			else:
				value = await field.read(decode=True)
			ov = ns.get(field.name)
			if ov:
				if type(ov) == type([]):
					ov.append(value)
				else:
					ov = [ov,value]
			else:
				ov = value
			ns.update({field.name:ov})
		return ns

	async def _handle(self,request:Request) -> StreamResponse:
		name = str(request.url)
		t = TimeCost(name)
		with t:
			x = await self._handle1(request)
		print(timestampstr(),':',name,':', 'time cost=', t.end_time - t.begin_time)
		return x
		
	async def _handle1(self,request:Request) -> StreamResponse:
		clientkeys = {
			"iPhone":"iphone",
			"iPad":"ipad",
			"Android":"androidpad",
			"Windows Phone":"winphone",
			"Windows NT[.]*Win64; x64":"pc",
		}

		def i18nDICT():
			c = getConfig()
			g = ServerEnv()
			if not g.get('myi18n',False):
				g.myi18n = getI18N()
			lang = getHeaderLang(request)
			l = c.langMapping.get(lang,lang)
			return json.dumps(g.myi18n.getLangDict(l))

		def getClientType(request):
			agent = request.headers.get('user-agent')
			if type(agent)!=type('') and type(agent)!=type(b''):
				return 'pc'
			for k in clientkeys.keys():
				m = re.findall(k,agent)
				if len(m)>0:
					return clientkeys[k]
			return 'pc'

		def serveri18n(s):
			lang = getHeaderLang(request)
			c = getConfig()
			g = ServerEnv()
			if not g.get('myi18n',False):
				g.myi18n = getI18N()
			l = c.langMapping.get(lang,lang)
			return g.myi18n(s,l)

			
		async def getArgs():
			ns = DictObject()
			if request.method == 'POST':
				return await self.getPostData(request)
			ns = multiDict2Dict(request.query)
			return ns

		self.y_env.i18n = serveri18n
		self.y_env.i18nDict = i18nDICT
		self.y_env.terminalType = getClientType(request)
		self.y_env.entire_url = partial(self.entireUrl,request)
		self.y_env.abspath = self.abspath
		self.y_env.request2ns = getArgs
		self.y_env.resource = self
		self.y_env.gethost = partial(self.gethost, request)
		self.y_env.path_call = partial(self.path_call,request)
		self.user = await auth.get_auth(request)
		self.y_env.user = self.user
		self.request_filename = self.url2file(str(request.url))
		path = request.path
		config = getConfig()
		if config.website.dbadm and path.startswith(config.website.dbadm):
			pp = path.split('/')[2:]
			if len(pp)<3:
				print(str(request.url), 'not found')
				raise HTTPNotFound
			dbname = pp[0]
			tablename = pp[1]
			action = pp[2]
			adm = DBAdmin(request,dbname,tablename,action)
			return await adm.render()
		if config.website.dbrest and path.startswith(config.website.dbrest):
			pp = path.split('/')[2:]
			if len(pp)<2:
				print(str(request.url), 'not found')
				raise HTTPNotFound
			dbname = pp[0]
			tablename = pp[1]
			id = None
			if len(pp) > 2:
				id = pp[2]
			crud = DBCrud(request,dbname,tablename,id=id)
			return await crud.dispatch()
		if config.website.download and path.startswith(config.website.download):
			pp = path.split('/')[2:]
			if len(pp)<1:
				print(str(request.url), 'not found')
				raise HTTPNotFound
			dp = '/'.join(pp)
			path = path_decode(dp)
			return await file_download(request, path)

		# processor = self.url2processor(request, str(request.url))
		processor = self.url2processor(request, str(request.url), self.request_filename)
		if processor:
			return await processor.handle(request)

		if self.request_filename and self.isHtml(self.request_filename):
			return await self.html_handle(request, self.request_filename)

		if self.request_filename and os.path.isdir(self.request_filename):
			config = getConfig()
			if not config.website.allowListFolder:
				print(str(request.url), 'not found')
				raise HTTPNotFound
		return await super()._handle(request)

	def gethost(self, request):
		host = request.headers.get('X-Forwarded-Host')
		if host:
			return host
		host = request.headers.get('Host')
		if host:
			return host
		return '/'.join(str(request.url).split('/')[:3])
		
	async def html_handle(self,request,filepath):
		with open(filepath,'rb') as f:
			b = f.read()
			utxt = b.decode('unicode_escape')
			txt = b.decode('utf-8')
			headers = {
				'Content-Type': 'text/html; utf-8',
				'Accept-Ranges': 'bytes',
				'Content-Length': str(len(utxt))
			}
			resp = Response(text=txt,headers=headers)
			return resp
			
	def isHtml(self,fn):
		try:
			with codecs.open(fn,'r','utf-8') as f:
				b = f.read()
				while b[0] in ['\n',' ','\t']:
					b = b[1:]
				if b.lower().startswith('<html>'):
					return True
				if b.lower().startswith('<!doctype html>'):
					return True
		except Exception as e:
			return False
		
	def url2processor(self, request, url, fpath):
		config = getConfig()
		url = self.entireUrl(request, url)
		host =  '/'.join(str(request.url).split('/')[:3])
		path = url[len(host):].split('?')[0]
		real_path = self.abspath(request, path)
		if config.website.startswiths:
			for a in config.website.startswiths:
				if path.startswith(a.leading):
					processor = FunctionProcessor(path,self,a)
					return processor

		if self.request_filename is None:
			print(url, 'not found')
			raise HTTPNotFound
			
		for word, handlername in self.y_processors:
			if fpath.endswith(word):
				Klass = getProcessor(handlername)
				processor = Klass(path,self)
				return processor
		return None

	def entireUrl(self, request, url):
		if url.startswith('http://') or url.startswith('https://'):
			return url
		h = self.gethost(request)
		if url.startswith('/'):
			return '%s://%s%s' % (request.scheme, h, url)
		path = request.path
		if self.request_filename and os.path.isdir(self.request_filename):
			path = '%s/oops' % path
		p = self.relatedurl(path,url)
		return '%s://%s%s' % (request.scheme, h, p)

	async def path_call(self, request, path, params={}):
		url = self.entireUrl(request, path)
		
		fpath = self.url2file(url)
		processor = self.url2processor(request, url, fpath)
		return await processor.path_call(request, params=params)
		
