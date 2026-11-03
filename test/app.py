import asyncio
from ahserver.webapp import webapp
from ahserver.configuredServer import add_cleanupctx
from appPublic.zmqapi import run_proxy

async def worker(app):
	x = 100
	print('worker go ....')
	while True:
		print(f'worker alive {x}')
		await asyncio.sleep(30)

async def background_coro(app):
	print('here')
	task = asyncio.create_task(run_proxy())
	app['mytask'] = task
	print('before yield')
	yield
	print('after yield')
	task.cancel()

def init():
	add_cleanupctx(background_coro)

if __name__ == '__main__':
	webapp(init)
	
