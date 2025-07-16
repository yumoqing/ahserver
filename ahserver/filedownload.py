import os
import asyncio

import aiofiles
import mimetypes
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web import StreamResponse
from aiohttp import web
from appPublic.rc4 import RC4
from appPublic.registerfunction import RegisterFunction
from appPublic.log import debug
from .filestorage import FileStorage

crypto_aim = 'God bless USA and others'
def path_encode(path):
	rc4 = RC4()
	return rc4.encode(path,crypto_aim)

def path_decode(dpath):
	rc4 = RC4()
	return rc4.decode(dpath,crypto_aim)

async def file_upload(request):
	pass

async def file_handle(request, filepath, download=False):
	filename = os.path.basename(filepath)
	debug(f'{filepath=}, {filename=}, {download=}')
	headers = {}
	if download:
		headers = {
		'Content-Disposition': f'attachment; filename="{filename}"'
		}
	r = web.FileResponse(filepath, chunk_size=8096, headers=headers)
	r.enable_compression()
	return r

async def file_download(request, filepath):
	return await file_handle(request, filepath, download=True)

async def path_download(request, params_kw, *params, **kw):
	path = params_kw.get('path')
	download = False
	if params_kw.get('download'):
		download = True
	fs = FileStorage()
	fp = fs.realPath(path)
	debug(f'path_download():download filename={fp}')
	return await file_handle(request, fp, download)

rf = RegisterFunction()
rf.register('idfile', path_download)
rf.register('download', path_download)
