import os
import asyncio

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

async def file_download(request, filepath):
	filename = os.path.basename(filepath)
	if os.path.exists(filepath):
		response = web.StreamResponse(
			status=200,
			reason='OK',
			headers={'Content-Type': 'text/plain',
				'Content-Disposition': 'attrachment;filename={}'.format(filename)
			},
		)
		await response.prepare(request)
		
		async with aiofile.AIOFile(filepath, 'rb') as f:
			while True:
				x = await f.read()
				if x is None:
					break
				await response.write(x)
		await response.write_eof()
		return response
	raise HTTPNotFound

