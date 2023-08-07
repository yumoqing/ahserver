import os
import sys

from appPublic.folderUtils import listFile
from appPublic.ExecFile import ExecFile
from ahserver.serverenv import ServerEnv

def load_plugins(p_dir):
	ef = ExecFile()
	pdir = os.path.join(p_dir, 'plugins')
	if not os.path.isdir(pdir):
		print('load_plugins:%s not exists' % pdir)
		return
	sys.path.append(pdir)
	ef.set('sys',sys)
	ef.set('ServerEnv', ServerEnv)
	for m in listFile(pdir, suffixs='.py'):
		if m.endswith('__init__.py'):
			continue
		print('module=', module)
		module = os.path.basename(m[:-3])
		__import__(module, locals(), globals())

