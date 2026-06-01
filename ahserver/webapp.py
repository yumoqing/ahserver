import os, sys
try:
	import uvloop
	if sys.platform != 'win32':
		uvloop.install()
except Exception as e:
	pass
from appPublic.log import MyLogger, info, debug, warning
import argparse
from appPublic.folderUtils import ProgramPath
from appPublic.jsonConfig import getConfig
from appPublic.event_dispatcher import EventDispatcher
from sqlor.dbpools import DBPools
from ahserver.configuredServer import ConfiguredServer
from ahserver.serverenv import ServerEnv
from appPublic.jsonConfig import getConfig
		
def webapp(init_func, app=None):
	parser = argparse.ArgumentParser(prog="Sage")
	parser.add_argument('-w', '--workdir')
	parser.add_argument('-p', '--port')
	args = parser.parse_args()
	workdir = args.workdir or os.getcwd()
	port = args.port
	webserver(init_func, workdir, port=port, app=app)

def webserver(init_func, workdir, port=None, app=None):
	p = ProgramPath()
	config = getConfig(workdir, NS={'workdir':workdir, 'ProgramPath':p})
	if config.logger:
		logger = MyLogger(config.logger.name or 'webapp',
							levelname=config.logger.levelname or 'info',
							logfile=config.logger.logfile or None)
	else:
		logger = MyLogger('webapp', levelname='info')
	DBPools(config.databases)
	# Create EventDispatcher BEFORE init_func() so all load_XXX() can bind
	se = ServerEnv()
	se.event_dispatcher = EventDispatcher()
	init_func()
	se.workdir = workdir
	se.port = port
	server = ConfiguredServer(workdir=workdir, app=app)
	port = port or config.website.port or 8080
	port = int(port)
	server.run(port=port)


if __name__ == '__main__':
	from main import main
	webapp(main)
