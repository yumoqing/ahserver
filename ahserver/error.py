def Error(errno='undefined error',msg='Error'):
	return {
		"status":"Error",
		"data":{
			"message":msg,
			"errno":errno
		}
	}

def Success(data):
	return {
		"status":"OK",
		"data":data
	}
