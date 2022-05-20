from appPublic.jsonConfig import getConfig
from appPublic.i18n import getI18N
from ahserver.filedownload import file_download

async def getPublicKey(*args, **kw):
	config = getConfig()
	request = options.request
	pf = config.website.rsakey.publickey
	return await file_download(request,pf)

async def getI18nMapping(*args, **kw):
	lang = args[0]
	i18n = getI18N()
	mapping = i18n.getLangDict(lang)
	return mapping
	
