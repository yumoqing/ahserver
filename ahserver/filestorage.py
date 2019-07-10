# fileUpload.py

import os
import time
import tempfile
import aiofile

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

	def _name2path(name):
		name = os.path.basename(name)
		paths=[191,193,197,199,97]
		v = int(time.time()*1000000)
		# b = name.encode('utf8') if not isinstance(name,bytes) else name
		# v = int.from_bytes(b,byteorder='big',signed=False)
		path = os.path.abspath(os.path.join(self.root,
					v % paths[0],
					v % paths[1],
					v % paths[2],
					v % paths[3],
					v % paths[4],
					name))
		return path

	async def save(name,read_data):
		p = self.name2path(name)
		_mkdir(os.path.dirname(p))
		async with aiofile.open(p,mode='rb') as f:
			while 1:
				d = await read_data()
				if not d:
					break
				await f.write(d)
				
		return p[len(self.root):]
