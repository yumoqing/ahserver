# fileUpload.py

import asyncio
import os
import time
import tempfile
import aiofiles
import json
import time
import base64

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
		self.loop = asyncio.get_event_loop()
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

async def downloadfile(url, headers=None, params=None, data={}):
	filename = url.split('/')[-1]
	fs = FileStorage()
	fpath = fs._name2path(filename, userid='tmp')
	try:
		shc = StreamHttpClient()
		async with aiofiles.open(fpath,'wb') as f:
			async for chunk in shc('GET', url,
					headers=headers, 
					params=params,
					data=data):
				f.write(chunk)
		return fpath
	except Exception as e:
		exception(f'save {url} to {fpath} exception:{e}'
		raise e

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


