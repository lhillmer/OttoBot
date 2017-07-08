from bot import DiscordWrapper
from webWrapper import WebWrapper
import globalSettings

import asyncio
import logging
import signal
import functools
import sys

logging.basicConfig(filename='example.log', level=logging.INFO)
stdout = logging.StreamHandler(sys.stdout)
stdout.setLevel(logging.INFO)
stdout.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: [%(name)s] %(message)s'))
_logger = logging.getLogger()
_logger.addHandler(stdout)

"""what's the difference between these two?"""
if hasattr(asyncio, "async"):
    ensure_future = asyncio.async
else:
    ensure_future = asyncio.ensure_future


class OttoBot:
    def __init__(self, token, prefix, commandsFile):
        self.loop = asyncio.get_event_loop()
        self.web = WebWrapper(self.loop)
        self.discord = DiscordWrapper(token, self.web, prefix, commandsFile)
        self.discord_task = None
        self.web_task = None
        self.shutdown_error = False
    
    def start(self):
        _logger.info("Starting OttoBot")
        
        def begin_shutdown(signame):
            is_error = True if signame == "SIGTERM" else False
            msg = "Shutting down bot due to signal: {}".format(signame)
            if is_error:
                _logger.error(msg)
            else:
                _logger.info(msg)
            self.stop(is_error)
      
        """make sure the primary loop is interruptable"""
        for signame in ("SIGINT", "SIGTERM"):
            """windows doesn't have signals, so this will error if running on windows"""
            try:
                self.loop.add_signal_handler(getattr(signal, signame),functools.partial(begin_shutdown, signame))
            except NotImplementedError:
                pass

        self.discord_task = ensure_future(self.discord.start())
        self.web_task = ensure_future(self.web.run())
        
        try:
            self.loop.run_until_complete(self.process())
        except asyncio.CancelledError:
            pass
        
        self.loop.close()
        sys.exit(self.shutdown_error)
    
    def stop(self, is_error=False):
        _logger.info("Stopping OttoBot")
        self.shutdown_error = is_error
        
        if self.discord_task and not self.discord_task.done():
            ensure_future(self.discord.disconnect(True))
    
    async def process(self):
        
        while True:
            await asyncio.wait([self.web_task, self.discord_task], return_when=asyncio.FIRST_COMPLETED)


def main():
    globalSettings.init()
    bot = OttoBot(globalSettings.config.get('DEFAULT', 'token'),
            globalSettings.config.get('DEFAULT', 'prefix'),
            globalSettings.config.get('DEFAULT', 'commandsFile'))
    bot.start()

main()
