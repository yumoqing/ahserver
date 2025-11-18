# ahserver服务模块扩展

用ahserver和bricks开发h5规范的web应用，模块需要遵守以下约素:

* 模块目录必须符合下面的模块目录结构要求

* 函数export，定义模块可被dspy和ui或其他模块调用函数

## 函数export
```
from ahserver.serverenv import ServerEnv
from appPublic.worker import awaitify
from .x import a, b, c	# a，b, c是协程
from .y import x, y		# x, y是普通函数

def load_mymodule(): # mymodule需替换为实际的模块名字
	env = ServerEnv()
	env.a = a		# 脚本中用"a" 调用"a"
	env.b = b		# 脚本中用"b"调用"b"
	env.cc = c		# 脚本中用"cc"调用"c"
	env.y = awaitify(y)	# 将函数包装为协程
	env.x = awaitify(x) # 将函数包装为协程
```

## 目录结构
```
mymodule
    ｜
	+--mymodule目录			# python module 目录
	｜    ｜  
	｜    +--init.py		# 模块初始化脚本，需要定义一个load_mymodule()函数，此函数需要将在ui和dspy文件中用到的函数通过ServerEnv实例传过去
	｜    ｜
	｜    +--__init__.py	#python模块所需
	｜
	+--wwwroot目录			# web服务脚本，文件以.ui和.dspy结束，ui文件支持jinja2模板，前端控件文件，内容为json格式的控件描述文本， dspy是ahserver支持的受限python脚本，可以按照需要设置下级目录
	｜
	+--models目录			# 模块使用的数据表以.xlsx后缀存放在此目录中
	｜
	+--json目录				# 存放json文件，定义数据表的CRUD逻辑
	｜
	+--pyproject.toml文件	# pip打包文件, 其中项目名字与mymodule相同
	｜
	+--README.md文件		# 模块自说明文件
	｜
	+--init目录				# 模块初始化目录
	    ｜
		+--data.xlsx		# 初始化数据，一个sheet一个表，一行一个记录，第一行为字段名
		｜
		+--script.py		# 初始化脚本
```

## 数据表文件说明
数据表文件也是模块的源码，文件名称放在二级标题上，内容包括：
* 表功能说明

* 数据字段列表

## 数据表crud的json文件

模块中的每个数据表都需要一个json文件，放在模块的json目录下

数据表json文件也是模块的源码，文件名称放在二级标题上，内容包括

* 树状结构或列表结构

* 哪些字段列表不显示

* 哪些字段编辑时不编辑

* 哪些字段时敏感信息

* 本表的主键是哪些表的外键,以{field: subtable_field, subtable: thattable} 形式给出


## 代码分布要求

* 模块中的主要逻辑用py源码实现，放在mymodule目录下

* 客户端业务功能放在wwwroot目录下，以.ui后缀结束，用jinja2执行服务器端逻辑

* 返回客户端数据的功能放在wwwroot目录下，以.dspy后缀结束

## ui, dspy可以直接使用的变量

### request 
aiohttp.Request实例，每个客户端请求有一个独立的Request实例

request._run_ns可以获得所有在.ui和.dspy源码中可以使用的变量，通过ahserver.ServerEnv 传递

### params_kw
DictObject（dict子类, 支持a.b方式获取属性）实例，接收到客户端传来的数据，如果有文件，文件都保存在服务器指定的位置，params_kw中属性名保存的是其相对路径，可用FileStorage().realPath(params_kw.myfile)来获得文件在服务器中的实际路径。

### get_user()
来自rbac模块，协程函数，获得当前登录用户，如果用户没有登录，返回None

### get_userorgid()
来自rbac模块，协程函数，获得当前登录用户的机构id，如果用户没有登录，返回None

### pyproject.toml和README.md
编写完成的pyproject.toml文件和README.md文件

