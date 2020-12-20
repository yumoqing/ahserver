import os
import asyncio

import mimetypes
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web import StreamResponse
from aiohttp import web
import aiofile

from appPublic.rc4 import RC4

crypto_aim = 'God bless USA and others'
def path_encode(path):
	rc4 = RC4()
	return rc4.encode(path,crypto_aim)

def path_decode(dpath):
	rc4 = RC4()
	return rc4.decode(dpath,crypto_aim)

async def file_download(request, filepath, content_type=None):
	filename = os.path.basename(filepath)
	r = web.FileResponse(filepath)
	ct = content_type
	if ct is None:
		ct, encoding = mimetypes.guess_type(filepath)
	if ct is not None:
		r.content_type = ct
	else:
		r.content_type = 'application/octet-stream'
	r.content_disposition = 'attachment; filename=%s' % filename
	r.enable_compression()
	return r
	if os.path.exists(filepath):
		length = os.path.getsize(filepath)
		response = web.Response(
			status=200,
			headers = {
			'Content-Disposition': 'attrachment;filename={}'.format(filename)
		}
		)
		await response.prepare(request)
		cnt = 0
		with open(filepath, 'rb') as f:
			chunk = f.read(10240000)
			cnt = cnt + len(chunk)
			await response.write(chunk)
		await response.fsyn()
		await response.write_eof()
		return response
	raise HTTPNotFound

