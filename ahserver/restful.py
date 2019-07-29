import os
import re

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

DEFAULT_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE')

class RestEndpoint:

	def __init__(self):
		self.methods = {}

		for method_name in DEFAULT_METHODS:
			method = getattr(self, method_name.lower(), None)
			if method:
				self.register_method(method_name, method)

	def register_method(self, method_name, method):
		self.methods[method_name.upper()] = method

	async def dispatch(self):
		method = self.methods.get(self.request.method.upper())
		if not method:
			raise HTTPMethodNotAllowed('', DEFAULT_METHODS)

		return await method()


class DBCrud(RestEndpoint):
	def __init__(self, request,dbname,tablename, id=None):
		print(f'***{dbname}*{tablename}*{id}************')
		super().__init__()
		self.dbname = dbname
		self.tablename = tablename
		self.request = request
		self.id = id
		try:
			self.crud = CRUD(dbname,tablename)
		except Exception as e:
			print('e=',e)
			raise HTTPNotFound
		
	async def options(self) -> Response:
		try:
			d = await self.crud.I()
			return json_response(Success(d))
		except Exception as e:
			print(e)
			return json_response(Error(errno='metaerror',msg='get metadata error'))

	async def get(self) -> Response:
		"""
		query data
		"""
		try:
			ns = multiDict2Dict(self.request.query)
			if self.id is not None:
				ns['__id'] = self.id
			d = await self.crud.R(NS=ns)
			return json_response(Success(d))
		except Exception as e:
			print(e)
			return json_response(Error(errno='search error',msg='search error'))

	async def post(self):
		"""
		insert data
		"""
		try:
			ns = multiDict2Dict(await self.request.post())
			d = await self.crud.C(ns)
			return json_response(Success(d))
		except Exception as e:
			print(e)
			return json_response(Error(errno='add error',msg='add error')) 

	async def put(self):
		"""
		update data
		"""
		try:
			ns = multiDict2Dict(await self.request.post())
			d = await self.crud.U(ns)
			return json_response(Success(''))
		except Exception as e:
			print(e)
			return json_response(Error(errno='update error',msg='update error'))
		
	async def delete(self, request: Request, instance_id):
		"""
		delete data
		"""
		try:
			ns = multiDict2Dict(self.request.query)
			d = await self.crud.D(ns)
			return json_response(Success(d))
		except Exception as e:
			print(e)
			return json_response(Error(erron='delete error',msg='error'))
