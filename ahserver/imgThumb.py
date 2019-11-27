from PIL import Image
from io import BytesIO

def imageThumb(imgfilepath,width=None,height=None):
	im = Image.open(imgfilepath)
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
		height = int(float(width) * float(h) / float(w))
	else:
		width = int(float(height) * float(w) / float(h))
	thumb = im.resize((width,height),Image.ANTIALIAS)
	f = BytesIO()
	thumb.save(f,format='jpeg',quality=60)
	im.close()
	v = f.getvalue()
	with open('thumb.jpg','wb') as x:
		x.write(v)
	return v


if __name__ == '__main__':
	imageThumb("/home/ymq/media/pictures/2019-08/IMG_20190804_113014.jpg", width=256)
