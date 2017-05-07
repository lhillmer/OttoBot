import aiohttp
import asyncio
import async_timeout

import logging

_logger = logging.getLogger()

class WebWrapper():
	def __init__(self, loop):
		self.session = aiohttp.ClientSession(loop=loop)
		self.crawlServer = 'http://crawl.akrasiac.org'
		self.requests = []

	def disconnect(self):
		if self.session and not self.session.closed:
			self.session.close()


	async def run(self):
		_logger.info("Starting Web Wrapper")
		while True:
			if len(self.requests) != 0:
				req = self.requests.pop(0)
				await req

			#let other async tasks run
			await asyncio.sleep(0.1)


	async def fetch(self, url, timeout):
		_logger.info("http request to [" + url + "] with timeout " + str(timeout))
		with async_timeout.timeout(timeout):
			async with self.session.get(url) as response:
				_logger.info("got response from [" + url + "] with status: " + str(response.status))
				return response

	async def singleUseSession(self, url, timeout):
		loop = asyncio.get_event_loop()
		async def inner():
			async with aiohttp.ClientSession(loop=loop) as session:
				return await self.fetch(session, url, timeout)
		task = loop.create_task(inner())
		return await task

	async def queueRequest(self, url, timeout):
		_logger.info("queueing up request for url [" + url + "]")
		coro = self.fetch(url, timeout)
		self.requests.append(coro)
		result = await coro
		_logger.info("request for url[" + url + "] has popped")
		return result

	'''this code might be totally awful. I still don't fully understand async shenanigans'''
	'''ideally this should be a non-blocking http request. I doubt it's actually set up properly to exhibit that behavior right now though'''
	async def doesCrawlUserExist(self, username):
		_logger.info("checking existence of crawl user: " + username)
		response = await self.queueRequest(self.crawlServer + '/rawdata/' + username + '/', 5)
		_logger.info("received response when checking for crawl user: " + username)
		return response.status == 200