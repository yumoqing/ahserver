import os
import re

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
from appPublic.MiniI18N import getI18N
from appPublic.dictObject import DictObject, multiDict2Dict

from .baseProcessor import getProcessor
from .xlsxdsProcessor import XLSXDataSourceProcessor
from .sqldsProcessor import SQLDataSourceProcessor
from .serverenv import ServerEnv
from .url2file import Url2File
from .filestorage import FileStorage
from .restful import DBCrud
from .filedownload import file_download, path_decode

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

class ProcessorResource(StaticResource):
	def __init__(self, prefix: str, directory: PathLike,
                 *, name: Optional[str]=None,
                 expect_handler: Optional[_ExpectHandler]=None,
                 chunk_size: int=256 * 1024,
                 show_index: bool=False, follow_symlinks: bool=False,
                 append_version: bool=False)-> None:
		super().__init__(prefix, directory,
                 name=name,
                 expect_handler=expect_handler,
                 chunk_size=chunk_size,
                 show_index=show_index, 
				 follow_symlinks=follow_symlinks,
                 append_version=append_version)
		gr = self._routes.get('GET')
		self._routes.update({'POST':gr})
		self._routes.update({'PUT':gr})
		self._routes.update({'OPTIONS':gr})
		self._routes.update({'DELETE':gr})
		self._routes.update({'TRACE':gr})
		self.y_processors = []
		self.y_prefix = prefix
		self.y_directory = directory
		self.y_indexes = []
		self.y_env = DictObject()
		
	def setProcessors(self, processors):
		self.y_processors = processors

	def setIndexes(self, indexes):
		self.y_indexes = indexes

	def abspath(self,path:str):
		path = path[len(self.y_prefix):]
		if len(path)>0 and path[0] == '/':
			path = path[1:]
		rp = os.path.join(self.y_directory , path)
		real_path = os.path.abspath(rp)
		return real_path

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
		self.y_env.absurl = self.absUrl
		self.y_env.abspath = self.abspath
		self.y_env.request2ns = getArgs
		self.y_env.resource = self
		path = request.path
		config = getConfig()
		if config.website.dbrest and path.startswith(config.website.dbrest):
			pp = path.split('/')[2:]
			if len(pp)<2:
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
				raise HTTPNotFound
			dp = '/'.join(pp)
			path = path_decode(dp)
			print('path=',path)
			return await file_download(request, path)
			
		for word, handlername in self.y_processors:
			if path.endswith(word):
				Klass = getProcessor(handlername)
				processor = Klass(self.abspath(path),self)
				return await processor.handle(request)
		print(f'path={path} handler by StaticResource..')
		return await super()._handle(request)
		
	def absUrl(self,request,url):
		http='http://'
		https='https://'
		if url[:7] == http:
			return url
		if url[:8] == https:
			return url

		path = request.path
		return self.relatedurl(path,url)

