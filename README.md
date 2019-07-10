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

## Requirements

see requirements.txt

[pyutils](https://github.com/yumoqing/pyutils)

[sqlor](https://github.com/yumoqing/sqlor)

## How to use
see ah.py

```
from ahserver.configuredServer import ConfiguredServer

if __name__ == '__main__':
	server = ConfiguredServer()
	server.run()
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

## environment for processors

When coding in processors, ahserver provide some environment stuff for build apllication, there are modules, functions, classes and variables


### modules:
* time
* datetime
* random
* json

### functions:
* configValue
* isNone
* int
* str
* float
* type
* str2date
* str2datetime
* curDatetime
* uuid
* runSQL
* runSQLPaging
* runSQLIterator
* runSQLResultFields
* getTables
* getTableFields
* getTablePrimaryKey
* getTableForignKeys
* folderInfo
* abspath
* request2ns
* CRUD
* data2xlsx
* xlsxdata
* openfile
* i18n
* i18nDict
* absurl
* abspath
* request2ns

### variables
* resource
* terminalType

### classes
* ArgsConvert
