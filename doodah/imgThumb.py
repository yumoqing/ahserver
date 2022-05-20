import os
from PIL import Image, ExifTags
from io import BytesIO
from aiohttp.web_exceptions import (
	HTTPException,
	HTTPExpectationFailed,
	HTTPForbidden,
	HTTPMethodNotAllowed,
	HTTPNotFound,
)
from aiohttp.web_response import Response, StreamResponse
from id2file import getFilenameFromId


def imageUp(img):
	try:
		o = 'Orientation'
		exif=dict(img._getexif().items())
		if exif[o] == 3:
			img = img.rotate(180, expand=True)
		elif exif[o] == 6:
			img = img.rotate(270, expand=True)
		elif exif[o] == 8:
			img = img.rotate(90, expand=True)
		return img
	except (AttributeError, KeyError, IndexError):
		# cases: image don't have getexif
		return img

def imageThumb(imgfilepath,width=None,height=None):
	im = Image.open(imgfilepath)
	im = imageUp(im)
	mode = im.mode
	if mode not in ('L', 'RGB'):
		if mode == 'RGBA':
			alpha = im.split()[3]
			bgmask = alpha.point(lambda x: 255-x)
			im = im.convert('RGB')
			# paste(color, box, mask)
			im.paste((255,255,255), None, bgmask)
		else:
			im = im.convert('RGB')
			
	w, h = im.size
	if not width and not height:
		width = 256
	if width:
		width = int(width)
		height = int(float(width) * float(h) / float(w))
	else:
		height = int(height)
		width = int(float(height) * float(w) / float(h))
	thumb = im.resize((width,height),Image.ANTIALIAS)
	f = BytesIO()
	thumb.save(f,format='jpeg',quality=60)
	im.close()
	v = f.getvalue()
	return v

async def thumb(*args, **kw):
	id = args[0]
	request = kw.get('request')
	xpath = request.path[len(options.leading):]
	if xpath == '':
		raise HTTPNotFound
	id = xpath[1:]
	imgpath = await getFilenameFromId(id)
	v = imageThumb(imgpath,width=options.width,height=options.height)
	response = Response(
		status=200,
		headers = {
			'Content-Disposition': 'attrachment;filename={}'.format(os.path.basename(imgpath)),
			'Content-Length':str(len(v))
		}
	)
	await response.prepare(request)
	await response.write(v)
	await response.write_eof()
	return response
	
if __name__ == '__main__':
	imageThumb("/home/ymq/media/pictures/2019-08/IMG_20190804_113014.jpg", width=256)
