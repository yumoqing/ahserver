import os
import sys
from ahserver.configuredServer import ConfiguredServer

from appPublic.registerfunction import RegisterFunction
from appPublic.objectAction import ObjectAction
from ahserver.filedownload import path_encode
from imgThumb import thumb
from idFile import idFileDownload
from myauth import MyAuthAPI
from rf import getPublicKey, getI18nMapping
from loadplugins import load_plugins

def encodeFilepath(id,event,d):
	if d is None:
		return d

	if type(d) == type([]):
		return ArrayEncodeFilepath(d)

	d['rows'] = ArrayEncodeFilepath(d['rows'])
	return d
	
def ArrayEncodeFilepath(d):
	ret = []
	for r in d:
		r['name'] = path_encode(r['name'])
		ret.append(r)
	return ret

rf = RegisterFunction()
rf.register('makeThumb',thumb)
rf.register('idFileDownload',idFileDownload)
rf.register('getPublicKey', getPublicKey)
rf.register('getI18nMapping', getI18nMapping)

p = os.getcwd()
if len(sys.argv) > 1:
	p = sys.argv[1]
print('p=', p)
server = ConfiguredServer(auth_klass=MyAuthAPI,workdir=p)
load_plugins(p)
server.run()
