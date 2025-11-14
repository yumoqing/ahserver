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
	+--wwwroot目录			# web服务脚本，文件已.ui和.dspy结束，ui文件支持jinja2模板，前端控件文件，内容为json格式的控件描述文本， dspy是ahserver支持的受限python脚本，可以按照需要设置下级目录
	｜
	+--models目录			# xlsx格式的数据库描述文件，用开创建模块所需的数据库表
	｜
	+--json目录				# 存放json文件，定义数据表的CRUD逻辑
	｜
	+--pyproject.toml文件	# pip打包文件
	｜
	+--README.md文件		# 模块自说明文件
	｜
	+--init目录				# 模块初始化目录
	    ｜
		+--data.xlsx		# 初始化数据，一个sheet一个表，一行一个记录，第一行为字段名
		｜
		+--script.py		# 初始化脚本
```

