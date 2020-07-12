import os
import re
import traceback

from aiohttp.web_urldispatcher import StaticResource, _WebHandler, PathLike
from aiohttp.web_urldispatcher import Optional, _ExpectHandler
from aiohttp.web_urldispatcher import Path
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_exceptions import (
    HTTPException,
    HTTPExpectationFailed,
    HTTPForbidden,
    HTTPMethodNotAllowed,
    HTTPNotFound,
)
from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_routedef import AbstractRouteDef
from aiohttp.web import json_response


from sqlor.crud import CRUD

from appPublic.dictObject import multiDict2Dict
from appPublic.jsonConfig import getConfig

from .error import Error,Success
actions = [
	"browse",
	"add",
	"update",
	"filter"
]

class DBAdmin:
	def __init__(self, request,dbname,tablename, action):
		self.dbname = dbname
		self.tablename = tablename
		self.request = request
		self.action = action
		if action not in actions:
			print('action not defined',action)
			raise HTTPNotFound
		try:
			self.crud = CRUD(dbname,tablename)
		except Exception as e:
			print('e=',e)
			traceback.print_exc()
			raise HTTPNotFound
		
	async def render(self) -> Response:
		try:
			d = await self.crud.I()
			return json_response(Success(d))
		except Exception as e:
			print(e)
			traceback.print_exc()
			return json_response(Error(errno='metaerror',msg='get metadata error'))

