# fileUpload.py

import os
import time
import tempfile
import aiofiles

from appPublic.folderUtils import _mkdir
from appPublic.jsonConfig import getConfig

class FileStorage:
	def __init__(self):
		config = getConfig()
		self.root = config.filesroot or tempfile.gettempdir()
	
	def realPath(self,path):
		if path[0] == '/':
			path = path[1:]
		p = os.path.join(self.root,path)
		return p

	def _name2path(self,name):
		name = os.path.basename(name)
		paths=[191,193,197,199,97]
		v = int(time.time()*1000000)
		# b = name.encode('utf8') if not isinstance(name,bytes) else name
		# v = int.from_bytes(b,byteorder='big',signed=False)
		path = os.path.abspath(os.path.join(self.root,
					str(v % paths[0]),
					str(v % paths[1]),
					str(v % paths[2]),
					str(v % paths[3]),
					str(v % paths[4]),
					name))
		return path

	async def save(self,name,read_data):
		# print(f'FileStorage():save():{name=}')
		p = self._name2path(name)
		fpath = p[len(self.root):]
		_mkdir(os.path.dirname(p))
		async with aiofiles.open(p,'wb') as f:
			siz = 0
			while 1:
				d = await read_data()
				if not d:
					break
				siz += len(d);
				await f.write(d)
				await f.flush()
			print(f'{name=} file({fpath}) write {siz} bytes')
				
		return fpath
