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

def NeedLogin(path):
	return {
		"status":"need_login",
		"data":path
	}

def NoPermission(path):
	return {
		"status":"no_permission",
		"data":path
	}

def return_error(error_message):
	return {
		'status': 'error',
		'data': {
			'message': error_message
		}
	}

def return_ok(data):
	return {
		'status': 'ok',
		'data': data
	}

def openai_401():
	d = {
		"error": {
			"message": "Incorrect API key provided: sk-abc...xyz. You can find your API key at https://platform.openai.com/account/api-keys.",
			"type": "invalid_request_error",
			"param": null,
			"code": "invalid_api_key"
		}
	}
	return json_response(d, status=401)

def openai_403():
	d = {
		"error": {
			"message": "You don't have access to this model.",
			"type": "invalid_request_error",
			"param": null,
			"code": "model_not_found"
		}
	}
	return json_resposne(d, status=403)

def openai_429():
	d = {
		"error": {
			"message": "You exceeded your current quota, please check your plan and billing details.",
			"type": "insufficient_quota",
			"param": null,
			"code": "insufficient_quota"
		}
	}
	return json_response(d, status=429)

def openai_400():
	d = {
		"error": {
			"message": "Parameters error.",
			"type": "invalidparameters",
			"param": null,
			"code": "invalidparameters"
		}
	}
	
