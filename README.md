# ahserver

ahserver is a http(s) server base on aiohttp asynchronous framework.

ahserver capabilities:
* user authorization and authentication support
* https support
* processor for registed file type
* pre-defined variables and function can be called by processors
* multiple database connection and connection pool
* a easy way to wrap SQL
* configure data from  json file stored at ./conf/config.json
* upload file auto save under config.filesroot folder
* i18n support
* processors include:
	+ 'dspy' file subffix by '.dspy', is process as a python script
	+ 'tmpl' files subffix by '.tmpl', is process as a template
	+ 'md' files subffix by '.md', is process as a markdown file
	+ 'xlsxds' files subffix by '.xlsxds' is process as a data source from xlsx file
	+ 'sqlds' files subffixed by '.sqlds' is process as a data source from database via a sql command

## python3.12 bug fix
We use aioredis, it use distutils, but above 3.12, distutils not exists, so we need to hack it a bit.

### new model
```
pip install packaging
```
need modify files:
* aioredis/exceptions.py
* aioredis/connection.py
```replace aioredis/connection.py line 11 with
from packaging.version import Version as StrictVersion
```
replace aiotedis/exceptions.py 14 line with:
```
class TimeoutError(asyncio.TimeoutError, RedisError):
```

## Requirements

see requirements.txt

[pyutils](https://github.com/yumoqing/pyutils)

[sqlor](https://github.com/yumoqing/sqlor)

## Usage

```
import asyncio
from ahserver.webapp import webapp
from ahserver.configuredServer import add_startup

# task running all the time in background
async def bgwork(app) -> None:
	while True:
		await asyncio.sleep(sec)
		print('hahaha')

def get_module_dbname(modulename):
	return 'test'

def init():
	env = ServerEnv()
	# add background task
	add_startup(bgwork(10))
	env.get_module_dbname = get_module_dbname

if __name__ == '__main__':
	webapp(init)
```

## Folder structure

+ app
+ |-ah.py
+ |--ahserver
+ |-conf
+      |-config.json
+ |-i18n

## Configuration file content
ahserver using json file format in its configuration, the following is a sample:
```
{
	"databases":{
		"aiocfae":{
			"driver":"aiomysql",
			"async_mode":true,
			"coding":"utf8",
			"dbname":"cfae",
			"kwargs":{
					"user":"test",
					"db":"cfae",
					"password":"test123",
					"host":"localhost"
			}
		},
		"cfae":{
			"driver":"mysql.connector",
			"coding":"utf8",
			"dbname":"cfae",
			"kwargs":{
					"user":"test",
					"db":"cfae",
					"password":"test123",
					"host":"localhost"
			}
		}
	},
	"website":{
		"paths":[
			["$[workdir]$/../usedpkgs/antd","/antd"],
			["$[workdir]$/../wolon",""]
		],
		"host":"0.0.0.0",
		"port":8080,
		"coding":"utf-8",
		"ssl":{
			"crtfile":"$[workdir]$/conf/www.xxx.com.pem",
			"keyfile":"$[workdir]$/conf/www.xxx.com.key"
		},
		"indexes":[
			"index.html",
			"index.tmpl",
			"index.dspy",
			"index.md"
		],
		"visualcoding":{
			"default_root":"/samples/vc/test",
			"userroot":{
				"ymq":"/samples/vc/ymq",
				"root":"/samples/vc/root"
			},
			"jrjpath":"/samples/vc/default"
		},
		"processors":[
			[".xlsxds","xlsxds"],
			[".sqlds","sqlds"],
			[".tmpl.js","tmpl"],
			[".tmpl.css","tmpl"],
			[".html.tmpl","tmpl"],
			[".tmpl","tmpl"],
			[".dspy","dspy"],
			[".md","md"]
		]
	},
	"langMapping":{
		"zh-Hans-CN":"zh-cn",
		"zh-CN":"zh-cn",
		"en-us":"en",
		"en-US":"en"
	}
}
```

### database configuration
the ahserver using packages for database engines are:
* oracle:cx_Oracle
* mysql:mysql-connector
* postgresql:psycopg2
* sql server:pymssql

however, you can change it, but must change the "driver" value the the package name in the database connection definition.

in the databases section in config.json, you can define one or more database connection, and also, it support many database engine, just as ORACLE,mysql,postgreSQL.
define a database connnect you need follow the following json format.

* mysql or mariadb
```
                "metadb":{
                        "driver":"mysql.connector",
                        "coding":"utf8",
                        "dbname":"sampledb",
                        "kwargs":{
                                "user":"user1",
                                "db":"sampledb",
                                "password":"user123",
                                "host":"localhost"
                        }
                }
```
the dbname and "db" should the same, which is the database name in mysql database
* Oracle
```
		"db_ora":{
			"driver":"cx_Oracle",
			"coding":"utf8",
			"dbname":sampledb",
			"kwargs":{
				"user":"user1",
				"host":"localhost",
				"dsn":"10.0.185.137:1521/SAMPLEDB"
			}
		}
```

* SQL Server
```
                "db_mssql":{
                        "driver":"pymssql",
                        "coding":"utf8",
                        "dbname":"sampledb",
                        "kwargs":{
                                "user":"user1",
                                "database":"sampledb",
                                "password":"user123",
                                "server":"localhost",
                                "port":1433,
                                "charset":"utf8"
                        }
                }
```
* PostgreSQL
```
		"db_pg":{
			"driver":"psycopg2",
			"dbname":"testdb",
			"coding":"utf8",
			"kwargs":{
				"database":"testdb",
				"user":"postgres",
				"password":"pass123",
				"host":"127.0.0.1",
				"port":"5432"
			}
		}
```
### https support

In config.json file, config.website.ssl need to set(see above)

### website configuration
#### paths
ahserver can serve its contents (static file, dynamic contents render by its processors) resided on difference folders on the server file system.
ahserver finds a content identified by http url in order the of the paths specified by "paths" lists inside "website" definition of config.json file
#### processors
all the prcessors ahserver using, must be listed here.
#### host
by defaualt, '0.0.0.0'
#### port
by default, 8080
#### coding
ahserver recomments using 'utf-8'

### langMapping

the browsers will send 'Accept-Language' are difference even if the same language. so ahserver using a "langMapping" definition to mapping multiple browser lang to same i18n file


## international

ahserver using MiniI18N in appPublic modules in pyutils package to implements i18n support

it will search translate text in ms* txt file in folder named by language name inside i18n folder in workdir folder, workdir is the folder where the ahserver program resided or identified by command line paraments.

## performance

To be list here

## Behind the nginx
when ahserver running behind the nginx, nginx should be forward following header to ahserver

* X-Forwarded-For: client real ip
* X-Forwarded-Scheme: scheme in client browser
* X-Forwarded-Host: host in client browser
* X-Forwarded-Url: url in client browser
* X-Forwarded-Prepath: subfolder name if if ahserver is behind nginx and use subfolder proxy.

## environment for processors

When coding in processors, ahserver provide some environment stuff for build apllication, there are modules, functions, classes and variables

### session environment

* async get_user()
a coroutine to get userid if user not login, it return None
* async remember_user(userid, username='', userorgid='') 
a coroutine to set session user info: userid, name, orgid
* async forget_user()
a coroutine to forget session user information, and get_user() will return None
* async redirect(url)
a coroutine to redirect request to a new url
* entire_url(url)
a function to convert url to a url with http(s)://servername:port/repath/.... format, a outside url will return argument's url without change.
* aiohttp_client
aiohttp_client is aiohttp.client class to make a new request to other server
* gethost()
a function to get client ip
* async path_call(path, **kw)
a coroutine to call other source in server with path
* params_kw
dictionary to storages data tranafers from client. if files upload from client, upload file stored under the folder defined in configure file named by "files", the params_kw only storage the subpath under "files" defined folder.

### global environment


### modules:
* time
* datetime
* random
* json

### functions:
* configValue(k):
function return configuration file value in k, k is start with '.', examples: configValue('.website') will return website value in configuration file; configValue('.website.port') will return port under website in configuration file.

* isNone(v)
a function check v is or not None, if is return True, else return False
* int(v)
a function to convert v to integer
* str(v)
a function to convert v to string
* float(v)
a function to convert v to float
* type(v)
a function to get v's type
* str2date(dstr)
a function to convert string with "YYYY-MM-DD" format to datetime.datetime instance
* str2datetime(dstr)
a function to convert string with "YYYY-MM-DD" format to datetime.datetime instance
* curDatetime()
a function to get current date and time in datetime.datetime instsance
* uuid()
a function to get a uuid value
* DBPools()
a function to get a db connection from sqlor connection pool, further infor see [sqlor](https://git.kaiyuancloud.cn/yumoqing/sqlor)

all the databases it can connected to need to defiend in 'databases' in configuration file.

CRUD use case:

by use CRUD, the table must have a id field as primay key.

CRUD use case 1(insert data to table. in a insert.dspy file)
```
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	ns = {
		'id':uuid(),
		'field1':1
	}
	recs = await sor.C('tbl1', ns)
```

CRUD use case 2(update data in table. in a update.dspy file)
```
ns = params_kw.copy() # get data from client
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	await sor.U('tbl1', ns)
```
CRUD use case 3(delete data in table. in a delete.dspy file)
```
ns = {
	'id':params_kw.id
}
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	await sor.D('tbl1', ns)
```
CRUD use case 4(query date from table, in a search.dspy file)
```
ns = params_kw.copy()
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	recs = await sor.R('tbl1', ns)
	# recs is d list with element is a DictObject instance with all the table fields data
	return recs
```
CRUD use case 5(paging query data from table, in a search_paging.dspy file)
```
ns = params_kw.copy()
if ns.get('page') is None:
	ns['page'] = 1
if ns.get('sort') is None:
	ns['sort'] = 'id desc'
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	recs = await sor.RP('tbl1', ns)
	# recs is a DictObject instance with two keys: "total": result records, "rows" return data list
	# example:
	# {
	#    "total":423123,
	#    "rows":[ ..... ] max record is "pagerows" in ns, default is 80
	# }
	return recs
```

SQL EXECUTE use case 1
```
sql = "..... where id=${id}$ and field1 = ${var1}$ ..."
db = DBPools()
async with db.sqlorContext('dbname') as sor:
	r = await sor.sqlExe(sql, {'id':'iejkuiew', 'var1':1111})
	# if sql is a select command, r is a list with data returned, is a instance of DictObject
	....
```

SQL EXECUTE use case 2
```
sql = "..... where id=${id}$ and field1 = ${var1}$ ..."
db = DBPools()
async with db.sqlorContext('dbname') as sor:
	r = await sor.sqlPaging(sql, {'id':'iejkuiew', 
								'page':1,
								'pagerows':60,
								'sort':'field1',
								'var1':1111})
	# r is a DictObject instance with two keys: "total": result records, "rows" return data list
	# example:
	# {
	#    "total":423123,
	#    "rows":[ ..... ] max record is "pagerows" in ns, default is 80
	# }
	....
```

### variables
* resource
* terminalType

* ArgsConvert
* curDateString
* curTimeString
* monthfirstday
* strdate_add
* webpath
* stream_response
* rfexe
* basic_auth_headers
* format_exc
* realpath
* save_file
* async_sleep
* DictObject
* 

### classes
* ArgsConvert

## Hot Reload

ahserver supports automatic hot-reload of cached resources when source files change, without requiring server restart. This is especially useful during development and when deploying configuration changes to production.

### Enable Hot Reload

Add `hot_reload` configuration to `conf/config.json`:

```json
{
    "hot_reload": {
        "enabled": true,
        "interval": 2
    }
}
```

Or simply:
```json
{
    "hot_reload": true
}
```

- `enabled`: whether hot reload is active (default: true when object form is used)
- `interval`: seconds between file checks (default: 2)

### Trigger Sources

Hot reload is triggered by three sources:

1. **config.json mtime change** — automatically detected by FileWatcher
   - Clears `JsonConfig` singleton so next `getConfig()` call reloads from disk
   - **Does NOT dispatch `hot_reload` event** (modules caches are NOT cleared)
   - This is intentional: config changes rarely affect module cache validity

2. **i18n files mtime change** — automatically detected by FileWatcher
   - Clears `MiniI18N` singleton and `ServerEnv.myi18n` cache
   - **Dispatches `hot_reload` event** to all bound listeners

3. **HTTP endpoint** — manual trigger via `GET /__hot_reload__`
   - Writes to signal file `/tmp/.sage_cache_invalidate`
   - All workers detect signal file mtime change within their check interval
   - **Dispatches `hot_reload` event** to all bound listeners in all workers
   - Returns JSON response with confirmation

### Cross-Process Cache Invalidation

When running with `reuse_port=True` (multiple workers on same port), each process runs its own `HotReloader` instance. Cross-process cache invalidation works via signal file:

- `GET /__hot_reload__` writes timestamp to `/tmp/.sage_cache_invalidate`
- All workers detect mtime change within their check interval
- Each worker independently dispatches `hot_reload` event

This ensures all workers clear their caches without requiring IPC or shared memory.

### Event Name

The event dispatched is: **`hot_reload`**

Modules bind to this event to clear their caches. Example from `rbac` module:

```python
# In load_rbac() or init
env = ServerEnv()
if hasattr(env, 'event_dispatcher'):
    env.event_dispatcher.bind('hot_reload', env.userpermissions.on_hot_reload)
```

Handler signature:
```python
def on_hot_reload(data=None):
    """Event handler for hot_reload event. Clears all caches."""
    self.ur_caches.clear()
    self.invalidate_rp_cache()
```

The `data` parameter is a dict indicating what was reloaded:
- `{'config': True}` — config changed (not dispatched, modules won't see this)
- `{'i18n': True}` — i18n files changed
- `{'signal': True}` — signal file changed (cross-process)
- `{'source': 'http_endpoint'}` — HTTP endpoint triggered
- Multiple keys can be present

### What Gets Cleared

**Automatically cleared by ahserver:**
- `JsonConfig` singleton (on config.json change)
- `MiniI18N` singleton (on i18n file change)
- `ServerEnv.myi18n` cache (on i18n file change)

**Cleared by modules (via `hot_reload` event):**
- `rbac`: user permissions cache, role-permission cache
- `uapi`: API data cache, API keys cache, org users cache
- `pricing`: pricing program data cache
- `llmage`: UAPI cache

### Debug Logging

Set logger level to `debug` in `conf/config.json` to see hot reload activity:

```json
{
    "logger": {
        "name": "sage",
        "levelname": "debug",
        "logfile": "$[workdir]$/logs/sage.log"
    }
}
```

Key log messages:
- `[hot_reload] changed: {path}` — file mtime changed
- `[hot_reload] signal file changed, triggering reload` — signal file detected
- `[hot_reload] dispatching hot_reload event` — event will be dispatched
- `[hot_reload] config-only change, skipping cache clear dispatch` — config changed, no module cache clear
- `[module_name] on_hot_reload called, clearing caches` — module handler invoked

## Change logs

### 1.2.0
Use uvloop, httptools to speed up

### 1.0.8
#### server_error(errcode)
add a new global function named "server_error(errcode)", it will raise a HTTPException, errcode should be one of:
* 400	aiohttp.web.HTTPBadRequest	错误请求
* 401	aiohttp.web.HTTPUnauthorized	未认证
* 403	aiohttp.web.HTTPForbidden	禁止访问
* 404	aiohttp.web.HTTPNotFound	未找到
* 405	aiohttp.web.HTTPMethodNotAllowed	方法不允许
* 408	aiohttp.web.HTTPRequestTimeout	请求超时
* 409	aiohttp.web.HTTPConflict	冲突
* 410	aiohttp.web.HTTPGone	已删除
* 415	aiohttp.web.HTTPUnsupportedMediaType	不支持的媒体类型
* 429	aiohttp.web.HTTPTooManyRequests	请求过多
* 500	aiohttp.web.HTTPInternalServerError	服务器错误
* 502	aiohttp.web.HTTPBadGateway	错误网关
* 503	aiohttp.web.HTTPServiceUnavailable	服务不可用

else it will raise HTTPException exception
#### request._run_ns
global environment now can access from request._run_ns, it contains all the globals variable in ServerEnv and related variables of request 

