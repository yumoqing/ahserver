

import os

class Url2File:
	def __init__(self,path:str,prefix: str,
					indexes: list, inherit: bool=False):
		self.path = path
		self.starts = prefix
		self.indexes = indexes
		self.inherit = inherit

	def realurl(self,url:str) -> str :
		items = url.split('/')
		items = [ i for i in items if i != '.' ]
		while '..' in items:
			for i,v in enumerate(items):
				if v=='..' and i > 0:
					del items[i]
					del items[i-1]
					break
		return '/'.join(items)

	def isFolder(self,url: str) ->bool:
		if url.startswith(self.starts):
			rp = self.path + url[len(self.starts):]
			real_path = os.path.abspath(rp)
			if os.path.isdir(real_path):
				return True
		return False

	
	def isFile(self,url:str) ->bool:
		if url.startswith(self.starts):
			rp = self.path + url[len(self.starts):]
			real_path = os.path.abspath(rp)
			if os.path.isfile(real_path):
				return True
		return False


	def defaultIndex(self,url: str) -> str:
		for p in self.indexes:
			rp = url + '/' + p
			r = self.url2file(rp)
			if r is not None:
				return r
		return None

	def url2file(self,url: str):
		if url[-1] == '/':
			url = url[:-1]

		paths = url.split('/')[3:]
		f = os.path.join(self.path,*paths)
		real_path = os.path.abspath(f)
		if os.path.isdir(real_path):
			for idx in self.indexes:
				p = os.path.join(real_path,idx)
				if os.path.isfile(p):
					return p

		if os.path.isfile(real_path):
			return real_path

		if not self.inherit:
			return None
		items = url.split('/')
		if len(items) > 2:
			del items[-2]
			url = '/'.join(items)
			return self.url2file(url)
		return None

	def relatedurl(self,url: str, name: str) -> str:
		if url[-1] == '/':
			url = url[:-1]

		if not self.isFolder(url):
			items = url.split('/')
			del items[-1]
			url = '/'.join(items)
		url = url + '/' + name
		return self.realurl(url)

	def relatedurl2file(self,url: str, name: str):
		url = self.relatedurl(url,name)
		return self.url2file(url)

class TmplUrl2File(Url2File):
	def __init__(self,paths,indexes, subffixes=['.tmpl'],inherit=False):
		self.paths = paths
		self.u2fs = [ Url2File(p,prefix,indexes,inherit=inherit) \
						for p,prefix in paths ]
		self.subffixes = subffixes

	def url2file(self,url):
		for u2f in self.u2fs:
			fp = u2f.url2file(url)
			if fp:
				return fp
		return None

	def list_tmpl(self):
		ret = []
		for rp,_ in self.paths:
			p = os.path.abspath(rp)
			[ ret.append(i) for i in listFile(p,suffixs=self.subffixes,rescursive=True) ]	
		return sorted(ret)

