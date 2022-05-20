import os
import sys

from appPublic.folderUtils import listFile
from appPublic.ExecFile import ExecFile

def load_plugins(p_dir):
	ef = ExecFile()
	pdir = os.path.join(p_dir, 'plugins')
	if not os.path.isdir(pdir):
		print('load_plugins:%s not exists' % pdir)
		return
	sys.path.append(pdir)
	for py in listFile(pdir, suffixs=['.py'], rescursive=True):
		ef.set('sys',sys)
		ef.run(py)

