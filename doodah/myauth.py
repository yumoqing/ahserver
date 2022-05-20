from ahserver.auth_api import AuthAPI
from appPublic.jsonConfig import getConfig
from appPublic.registerfunction import getRegisterFunctionByName

class MyAuthAPI(AuthAPI):
	async def needAuth(self,path):
		config = getConfig()
		if not config.website.authpaths:
			return False
		for p in config.website.authpaths:
			if path.startswith(p):
				if not config.website.whitelist:
					return True
				for p1 in config.website.whitelist:
					if path.startswith(p1):
						return False
				return True
		return False

	async def checkUserPassword(self,user_id,password):
		config = getConfig()
		if config.users:
			for userid, passwd in config.users.items():
				if user_id == userid and password == passwd:
					print('******user passwd check OK****************')
					return True
		rf = getRegisterFunctionByName('user_password_check')
		if rf:
			return rf(user_id, password)

		return False

	async def getPermissionNeed(self,path):
		rf = getRegisterFunctionByName('get_need_permission')
		if rf:
			return rf(path)

		return 'ok'
	
	async def getUserPermissions(self,user):
		rf = getRegisterFunctionByName('get_user_permissions')
		if rf:
			return rf(user)

		return ['ok']
