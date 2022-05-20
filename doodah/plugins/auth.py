from appPublic.registerfunction import registerFunction

def user_password_check(user, password):
	return True

def get_need_permission(path):
	return 'perm'

def get_user_permissions(user):
	return ['perm']


registerFunction('user_password_check', user_password_check)
registerFunction('get_need_permission', get_need_permission)
registerFunction('get_user_permissions', get_user_permissions)

