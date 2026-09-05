# fileUpload.py

import asyncio
import os
import time
import tempfile
import aiofiles
import json
import time
import base64
from urllib.parse import quote
from appPublic.worker import get_event_loop
from appPublic.uniqueID import getID
from appPublic.qr import gen_qr, gen_qr_withlogo
from appPublic.folderUtils import _mkdir
from appPublic.base64_to_file import base64_to_file, getFilenameFromBase64
from appPublic.jsonConfig import getConfig
from appPublic.Singleton import SingletonDecorator
from appPublic.log import info, debug, warning, exception, critical
from appPublic.streamhttpclient import StreamHttpClient

@SingletonDecorator
class TmpFileRecord:
	def __init__(self, timeout=3600):
		self.filetime = {}
		self.changed_flg = False
		self.timeout = timeout
		self.time_period = 10
		self.filename = self.savefilename()
		self.loop = get_event_loop()
		self.loop.call_later(0.01, self.load)

	def newtmpfile(self, path:str):
		self.filetime[path] = time.time()
		self.change_flg = True

	def savefilename(self):
		config = getConfig()
		root = config.filesroot or tempfile.gettempdir()
		pid = os.getpid()
		return root + f'/tmpfile_rec_{pid}.json'

	async def save(self):
		if not self.change_flg:
			return
		async with aiofiles.open(self.filename, 'bw') as f:
			s = json.dumps(self.filetime, indent=4, ensure_ascii=False)
			b = s.encode('utf-8')
			await f.write(b)
			await f.flush()
			self.change_flg = False

	async def load(self):
		fn = self.filename
		if not os.path.isfile(fn):
			return
		async with aiofiles.open(fn, 'br') as f:
			b = await f.read()
			s = b.decode('utf-8')
			self.filetime = json.loads(s)

		self.remove()

	def file_useful(self, fpath):
		try:
			del self.filetime[fpath]
		except Exception as e:
			exception(f'Exception:{str(e)}')
			pass

	async def remove(self):
		tim = time.time()
		ft = {k:v for k,v in self.filetime.items()}
		for k,v in ft:
			if tim - v > self.timeout:
				self.rmfile(k)
				del self.tiletime[k]
		await self.save()
		self.loop.call_later(self.time_period, self.remove)

	def rmfile(self, name:str):
		config = getConfig()
		os.remove(config.fileroot + name)
	
class FileStorage:
	def __init__(self):
		config = getConfig()
		self.root = os.path.abspath(config.filesroot or tempfile.gettempdir())
		self.tfr = TmpFileRecord()
	
	def realPath(self,path):
		if path[0] == '/':
			path = path[1:]
		p = os.path.abspath(os.path.join(self.root,path))
		return p

	def save_base64_file(self, b64str):
		filename = getFilenameFromBase64(b64str)
		rfp = self._name2path(filename)
		base64_to_file(b64str, rfp)
		return rfp

	def webpath(self, path):
		if path.startswith(self.root):
			return path[len(self.root):]
		
	def _name2path(self,name, userid=None):
		name = os.path.basename(name)
		paths=[191,193,197,97]
		v = int(time.time()*1000000)
		# b = name.encode('utf8') if not isinstance(name,bytes) else name
		# v = int.from_bytes(b,byteorder='big',signed=False)
		root = self.root
		if userid:
			root += f'/{userid}'
		path = os.path.join(root,
					str(v % paths[0]),
					str(v % paths[1]),
					str(v % paths[2]),
					str(v % paths[3]))
		_mkdir(path)
		path = os.path.join(path, name)
		return path

	def remove(self, path):
		try:
			if path[0] == '/':
				path = path[1:]
			p = os.path.join(self.root, path)
			os.remove(p)
		except Exception as e:
			exception(f'{path=}, {p=} remove error')
			
	async def streaming_read(self, request, webpath, buf_size=8096):
		fp = self.realPath(webpath)
		stats = os.stat(fp)
		startpos = 0
		endpos = stats.st_size
		range = request.headers.get('Range')
		if range:
			range = range.split('=')[-1]
			s,e = range.split('-')
			if s:
				startpos = int(s)
			if e:
				endpos = int(e)
		debug(f'filesize={stats.st_size}, {startpos=}, {endpos=}')
		async with aiofiles.open(fp, 'rb') as f:
			if startpos > 0:
				await f.seek(startpos)
			pos = startpos
			while pos < endpos:
				b = await f.read(buf_size)
				yield b
				pos += len(b)

	async def save(self,name,read_data, userid=None):
		p = self._name2path(name, userid=userid)
		fpath = p[len(self.root):]
		info(f'{p=}, {fpath=},{self.root} ')
		_mkdir(os.path.dirname(p))
		if isinstance(read_data, str) or isinstance(read_data, bytes):
			b = read_data
			if isinstance(read_data, str):
				b = read_data.encode('utf-8')
			async with aiofiles.open(p, 'wb') as f:
				await f.write(b)
				await f.flush()
			self.tfr.newtmpfile(fpath)		
			return fpath

		async with aiofiles.open(p,'wb') as f:
			siz = 0
			while 1:
				d = await read_data()
				if not d:
					break
				siz += len(d);
				await f.write(d)
				await f.flush()
		self.tfr.newtmpfile(fpath)		
		return fpath

def file_realpath(path):
	fs = FileStorage()
	return fs.realPath(path)

async def downloadfile(url, headers=None, params=None, data={}, method='GET'):
	filename = url.split('/')[-1]
	filename = filename.split('?')[0]
	fs = FileStorage()
	fpath = fs._name2path(filename, userid='tmp')
	try:
		async with aiofiles.open(fpath,'wb') as f:
			shc = StreamHttpClient()
			"""
			async for chunk in shc(method, url,
					headers=headers, 
					params=params,
					data=data):
			"""
			async for chunk in shc(method, url):
				await f.write(chunk)
		return fpath
	except Exception as e:
		exception(f'save {url} to {fpath} exception:{e}')
		raise e

async def downloadfile2url(request, url, headers=None, params=None, data={}, method='GET'):
	fpath = await downloadfile(url, headers=headers, params=params, data=data, method=method)
	fs = FileStorage()
	webpath = fs.webpath(fpath)
	if request:
		env = request._run_ns
		url = env.entire_url('/idfile') + env.quote(webpath)
		return url
	baseurl = get_baseurl()
	if baseurl:
		return f'{baseurl}/idfile{quote(webpath)}'
	return f'/idfile{quote(webpath)}'

def get_baseurl():
	# 优先级：BASEURL（显式配置，多域名部署用） > _LAST_BASEURL（自动推导，单域名场景）
	baseurl = os.environ.get('BASEURL') or os.environ.get('_LAST_BASEURL')
	return baseurl

def webpath_to_base64(webpath):
	"""将 webpath 转为 base64 data URI，供 kimi 等多模态 uapi 使用"""
	import mimetypes
	fs = FileStorage()
	fp = fs.realPath(webpath)
	if not os.path.isfile(fp):
		return ''
	mime, _ = mimetypes.guess_type(fp)
	if not mime:
		mime = 'application/octet-stream'
	with open(fp, 'rb') as f:
		b64 = base64.b64encode(f.read()).decode('utf-8')
	return f'data:{mime};base64,{b64}'

async def base642file(b64str):
	filename = getFilenameFromBase64(b64str)
	if ',' in b64str:
		header, b64str = b64str.split(',', 1)
	fs = FileStorage()
	fpath = fs._name2path(filename, userid='tmp')
	async with aiofiles.open(fpath, 'wb') as f:
		binary_data = base64.b64decode(b64str)
		await f.write(binary_data)
	return fpath

async def b64media2url(request, mediafile):
	if mediafile.startswith('http://') or mediafile.startswith('https://'):
		return mediafile
	if mediafile.startswith('asset://'):
		return mediafile
	webpath = mediafile
	if mediafile.startswith('data:'):
		fpath = await base642file(mediafile)
		webpath = FileStorage().webpath(fpath)
	elif len(mediafile) > 8000:
		e = Exception(f'mediafile is not a media file')
		exception(f'{e}')
		return ''
	if request:
		entire_url = request._run_ns.entire_url
		url = entire_url('/idfile') + quote(webpath)
		return url
	baseurl = get_baseurl()
	if baseurl:
		return f'{baseurl}/idfile{quote(mediafile)}'
	return f'/idfile{quote(mediafile)}'

async def data2qrpath(data, logo=None):
	fs = FileStorage()
	qr_name = f'{getID()}.png'
	path = fs._name2path(qr_name)
	if logo:
		gen_qr_withlog(data, path, logo)
	else:
		gen_qr(data, path)
	return fs.webpath(path)

from .serverenv import ServerEnv
ServerEnv().webpath_to_base64 = webpath_to_base64


