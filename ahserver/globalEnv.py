# -*- coding:utf8 -*-
import os
import builtins
import sys
import codecs 
from urllib.parse import quote
import json
try:
	import uvloop
except:
	pass
import asyncio
from contextlib import asynccontextmanager

from aiohttp import BasicAuth
from aiohttp.client_exceptions import ClientConnectionResetError
from aiohttp.web import (
	HTTPException,
	HTTPBadRequest,
	HTTPUnauthorized,
	HTTPForbidden,
	HTTPNotFound,
	HTTPMethodNotAllowed,
	HTTPRequestTimeout,
	HTTPConflict,
	HTTPGone,
	HTTPUnsupportedMediaType,
	HTTPTooManyRequests,
	HTTPInternalServerError,
	HTTPBadGateway,
	HTTPServiceUnavailable,
	json_response,
	Response
	)
from traceback import format_exc
from functools import partial
from aiohttp_session import get_session

import random
import time
import datetime
from openpyxl import Workbook
from tempfile import mktemp
import base64

from appPublic.qr import gen_qr, gen_qr_withlogo
import base64
from appPublic.base64_to_file import hex2base64
from appPublic.jsonConfig import getConfig
from appPublic.dictObject import DictObject
from appPublic.Singleton import GlobalEnv
from appPublic.argsConvert import ArgsConvert
from appPublic.timeUtils import str2Date,str2Datetime,curDatetime, \
			getCurrentTimeStamp,curDateString, curTimeString, \
			monthfirstday, strdate_add, timestampstr, timestampAdd, timestampSub
from appPublic.dataencoder import quotedstr
from appPublic.folderUtils import folderInfo
from appPublic.uniqueID import setNode,getID
from appPublic.unicoding import unicoding,uDict,uObject
from appPublic.Singleton import SingletonDecorator
from appPublic.aes import aes_encode_b64, aes_decode_b64
from appPublic.registerfunction import RegisterFunction
from appPublic.httpclient import HttpClient
from appPublic.log import debug, exception
from appPublic.streamhttpclient import StreamHttpClient
from appPublic.zmqapi import zmq_publish

from sqlor.dbpools import DBPools, get_sor_context
from sqlor.filter import DBFilter, default_filterjson
from aiohttp.web import StreamResponse

from .xlsxData import XLSXData
from .uriop import URIOp
from .error import (
	Success, 
	Error, 
	NeedLogin, 
	NoPermission, 
	openai_401,
	openai_403,
	openai_429,
	openai_400,
	return_ok, 
	return_error
)

from .filetest import current_fileno
from .filedownload import path_download, file_download, file_response
from .filestorage import FileStorage, downloadfile2url, get_baseurl, b64media2url, data2qrpath
from .serverenv import ServerEnv

def server_error(errcode):
	exceptions = {
		400: HTTPBadRequest,
		401: HTTPUnauthorized,
		403: HTTPForbidden,
		404: HTTPNotFound,
		405: HTTPMethodNotAllowed,
		408: HTTPRequestTimeout,
		409: HTTPConflict,
		410: HTTPGone,
		415: HTTPUnsupportedMediaType,
		429: HTTPTooManyRequests,
		500: HTTPInternalServerError,
		502: HTTPBadGateway,
		503: HTTPServiceUnavailable
	}
	E = exceptions.get(errcode, HTTPException)
	raise E()

def basic_auth_headers(user, passwd):
	ba = BasicAuth(login=user, password=passwd)
	return {
		"Authorization":ba.encode()
	}

async def stream_response(request, async_data_generator, content_type='text/html',
						  keepalive_seconds=0):
	"""流式响应。

	keepalive_seconds:
		生成器静默超过该秒数时补发一帧心跳（<=0 = 关闭，默认关闭，需调用方显式开启）。
		目的：等待人工确认等长静默期不被浏览器/中间代理判定为死连接而切断。
		实测 2026-10-27 开发产线会话：确认等待 4 分 52 秒后连接被重置，
		整轮 agent 运行被取消（interrupted）。
		心跳帧按协议选型：SSE 用 ':' 注释帧（规范要求被忽略）；其余（JSON 行协议）
		用 '{"type":"ping"}' 行（前端按 JSON 行解析，':' 注释会让 JSON.parse 抛错）。

	2026-10-27 另修：write_eof() 原在断连保护之外，客户端已断开时必然再抛
	ClientConnectionResetError，异常传出会连同上游 agent run 一起取消并刷 Traceback。
	现在 write_eof 单独保护，断连只记 debug。
	"""
	res = StreamResponse()
	if content_type:
		res.content_type = content_type
	# 反代不缓冲（2026-10-27）：nginx proxy_buffering 默认 on，会把流式响应攒到
	# 结束才一起下发（用户观感「全部完成才显示，不能一行一行出」）。X-Accel-Buffering: no
	# 让 nginx 对该响应关闭缓冲，且不依赖各站点 conf 是否记得写 proxy_buffering off。
	res.headers['X-Accel-Buffering'] = 'no'
	res.headers['Cache-Control'] = 'no-cache, no-transform'
	await res.prepare(request)

	_ka = float(keepalive_seconds or 0)
	_is_sse = bool(content_type and 'event-stream' in str(content_type))
	_ka_frame = (': keepalive\n\n' if _is_sse else '{"type":"ping"}\n').encode('utf-8')

	gen = async_data_generator()
	# __anext__ 用 ensure_future 承载：等待超时后**不取消**它（取消＝取消上游 agent run），
	# 只补一帧心跳，下一轮继续等同一个 future。
	pending = asyncio.ensure_future(gen.__anext__())
	client_gone = False
	try:
		while True:
			if _ka > 0:
				done, _ = await asyncio.wait({pending}, timeout=_ka)
				if not done:
					try:
						await res.write(_ka_frame)
						await res.drain()
					except ClientConnectionResetError:
						client_gone = True
						break
					continue
			try:
				d = await pending
			except StopAsyncIteration:
				break
			except ClientConnectionResetError:
				client_gone = True
				break

			pending = asyncio.ensure_future(gen.__anext__())
			try:
				if isinstance(d, bytes):
					await res.write(d)
				elif isinstance(d, str):
					await res.write(d.encode('utf-8'))
				else:
					d = json.dumps(d, ensure_ascii=False)
					await res.write(d.encode('utf-8'))
			except ClientConnectionResetError:
				# 客户端已断开，静默忽略，不要 re-raise
				client_gone = True
				break
			except Exception as e:
				e = Exception(f'write error{e=}, {d=}')
				exception(f'{e}\n{format_exc()}')
				raise e
			await res.drain()
	finally:
		# 收掉未完成的 __anext__，避免残留的生成器（含 agent run）悬挂在事件循环里
		if not pending.done():
			pending.cancel()

	try:
		await res.write_eof()
	except ClientConnectionResetError:
		client_gone = True
	except Exception as e:
		exception(f'write_eof error {e=}\n{format_exc()}')

	if client_gone:
		# 客户端断开是常态（关页/切网/发新消息替换连接），不是服务端故障 → 只记 debug
		debug(f'stream_response: client disconnected, stream closed early')
	return res

def data2xlsx(rows,headers=None):
	wb = Workbook()
	ws = wb.active

	i = 1
	if headers is not None:
		for j in range(len(headers)):
			v = headers[j].title if headers[j].get('title',False) else headers[j].name
			ws.cell(column=j+1,row=i,value=v)
		i += 1
	for r in rows:
		for j in range(len(r)):
			v = r[headers[j].name]
			ws.cell(column=j+1,row=i,value=v)
		i += 1
	name = mktemp(suffix='.xlsx')
	wb.save(filename = name)
	wb.close()
	return name
	
async def save_file(str_or_bytes, filename):
	fs = FileStorage()
	r = await fs.save(filename, str_or_bytes)
	return r

def webpath(path):
	fs = FileStorage()
	return fs.webpath(path)

def realpath(path):
	fs = FileStorage()
	return fs.realPath(path)

class FileOutZone(Exception):
	def __init__(self,fp,*args,**kwargs):
		super(FileOutZone,self).__init__(*args,**kwargs)
		self.openfilename = fp
	
	def __str__(self):
		return self.openfilename + ': not allowed to open'
		
def get_config_value(kstr):
	keys = kstr.split('.')
	config = getConfig()
	if config is None:
		raise Exception('getConfig() error')
	for k in keys:
		config = config.get(k)
		if not config:
			return None
	return config

def get_definition(k):
	k = f'definitions.{k}'
	return get_config_value(k)

def openfile(url,m):
	fp = abspath(url)
	if fp is None:
		print(f'openfile({url},{m}),url is not match a file')
		raise Exception('url can not mathc a file')
	config = getConfig()
	paths = [ os.path.abspath(p) for p in config.website.paths ]
	fs = config.get('allow_folders',[])
	fs = [ os.path.abspath(i) for i in fs + paths ]
	r = False
	for f in fs:
		if fp.startswith(f):
			r = True
			break
	if not r:
		raise FileOutZone(fp)
	return open(fp,m)
	
def isNone(a):
	return a is None

def abspath(path):
	config = getConfig()
	paths = [ os.path.abspath(p) for p in config.website.paths ]
	for root in paths:
		p = root + path
		if os.path.exists(root+path):
			return p
			
	return None

def appname():
	config = getConfig()
	try:
		return config.license.app
	except:
		return "test app"
	
def configValue(ks):
	config = getConfig()
	try:
		a = eval('config' + ks)
		return a
	except:
		return None

def visualcoding():
	return configValue('.website.visualcoding');

def paramify(data, ns):
	ac = ArgsConvert('${', '}$')
	return ac.convert(data, ns)

def get_password_key():
	config = getConfig()
	return config.password_key or 'QRIVSRHrthhwyjy176556332'

def password_encode(s):
	k = get_password_key()
	return aes_encode_b64(k, s)

def password_decode(c):
	k = get_password_key()
	return aes_decode_b64(k, c)

@asynccontextmanager	
async def sqlorContext(module):
	db = DBPools()
	env = ServerEnv()
	dbname = env.get_module_dbname(module)
	async with db.sqlorContext(dbname) as sor:
		yield sor

def background_reco(reco, *args, **kw):
	asyncio.create_task(reco(*args, **kw))

def get_loop_type():
	loop = asyncio.get_event_loop()
	if uvloop:
		if isinstance(loop, uvloop.Loop):
			return 'uvloop.Loop'
	return str(type(loop))

def initEnv():
	g = ServerEnv()
	set_builtins()
	g.get_loop_type = get_loop_type
	rf = RegisterFunction()
	rf.register('i18n', i18n)
	g.paramify = paramify
	g.zmq_publish = zmq_publish
	g.configValue = configValue
	g.visualcoding = visualcoding
	g.uriop = URIOp
	g.isNone = isNone
	g.json = json
	g.ArgsConvert = ArgsConvert
	g.time = time
	g.curDateString = curDateString
	g.curTimeString = curTimeString
	g.datetime = datetime
	g.random = random
	g.str2date = str2Date
	g.str2datetime = str2Datetime
	g.timestampstr = timestampstr
	g.monthfirstday = monthfirstday
	g.curDatetime = curDatetime
	g.strdate_add = strdate_add
	g.uObject = uObject
	g.uuid = getID
	g.getID = getID
	g.folderInfo = folderInfo
	g.abspath = abspath
	g.data2xlsx = data2xlsx
	g.xlsxdata = XLSXData
	g.openfile = openfile
	g.DBPools = DBPools
	g.DBFilter = DBFilter
	g.default_filterjson = default_filterjson
	g.Error = Error
	g.Success = Success
	g.NeedLogin = NeedLogin
	g.NoPermission = NoPermission
	g.password_encode = password_encode
	g.password_decode = password_decode
	g.current_fileno = current_fileno
	g.get_config_value = get_config_value
	g.get_definition = get_definition
	g.DictObject = DictObject
	g.async_sleep = asyncio.sleep
	g.quotedstr = quotedstr
	g.quote = quote
	g.save_file = save_file
	g.realpath = realpath
	g.format_exc = format_exc
	g.basic_auth_headers = basic_auth_headers
	g.HttpClient = HttpClient
	g.rfexe = RegisterFunction().exe
	g.stream_response = stream_response
	g.webpath = webpath
	g.file_response = file_response
	g.file_download = file_download
	g.path_download = path_download
	g.partial = partial
	g.StreamHttpClient = StreamHttpClient
	g.server_error = server_error
	g.FileStorage = FileStorage
	g.downloadfile2url = downloadfile2url
	g.background_reco = background_reco
	g.get_sor_context = get_sor_context
	g.json_response = json_response
	g.Response = Response
	g.web_rootpath = web_rootpath
	g.return_ok = return_ok
	g.return_error = return_error
	g.openai_401 = openai_401
	g.get_baseurl = get_baseurl
	g.base64 = base64
	g.hex2base64 = hex2base64
	g.base64 = base64
	g.b64media2url = b64media2url
	g.openai_403 = openai_403
	g.openai_400 = openai_400
	g.openai_429 = openai_429
	g.timestampAdd = timestampAdd
	g.timestampSub = timestampSub
	g.data2qrpath = data2qrpath

def web_rootpath():
	config = getConfig()
	for fp, wp in config.website.paths:
		if wp == '':
			return fp
	return None

def i18n(request, *args, **kw):
	env = request._run_ns
	params_kw = env.params_kw
	root = web_rootpath()
	lang = params_kw.lang
	i18n_path = params_kw.i18n or 'i18n'
	fp = os.path.join(root , i18n_path, lang, 'i18n.json')
	try:
		with codecs.open(fp, 'r', 'utf-8') as f:
			return f.read()
	except Exception as e:
		exception(f'{params_kw=}, {e}')
		return {}

def set_builtins():
	all_builtins = [ i for i in dir(builtins) if not i.startswith('_')]
	g = ServerEnv()
	gg = globals()
	for l in all_builtins:
		exec(f'g["{l}"] = {l}',{'g':g})
