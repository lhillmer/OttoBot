import aiohttp
import asyncio
import async_timeout

async def fetch(session, url, timeout):
	with async_timeout.timeout(timeout):
		async with session.get(url) as response:
			return response

async def singleUseSession(loop, url, timeout):
	async with aiohttp.ClientSession(loop=loop) as session:
		return await fetch(session, url, timeout)

'''this code might be totally awful. I still don't fully understand async shenanigans'''
'''ideally this should be a non-blocking http request. I doubt it's actually set up properly to exhibit that behavior right now though'''
def doesCrawlUserExist(username):
	loop = asyncio.get_event_loop()
	result = loop.run_until_complete(singleUseSession(loop, 'http://crawl.akrasiac.org/rawdata/' + username + '/', 5))
	return result.status == 200