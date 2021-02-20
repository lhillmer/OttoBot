from bot import DiscordWrapper
from webWrapper import WebWrapper
import globalSettings

import asyncio
import logging
from logging import handlers
import signal
import functools
import sys
import os

handler = handlers.TimedRotatingFileHandler("logs/log_ottobot.log", when="midnight", interval=1)
format_string = '%(asctime)s,%(levelname)-8s [%(process)d][%(pathname)s:%(lineno)d] %(message)s'
handler.setFormatter(logging.Formatter(format_string))
handler.setLevel(logging.DEBUG)


logging.basicConfig(format=format_string,
    filename=os.devnull,
    level=logging.INFO)
_logger = logging.getLogger()
_logger.addHandler(handler)

ensure_future = asyncio.ensure_future

class OttoBot:
    def __init__(self, token, prefix, connectionString, spamLimit, spamTimeout, display_response_id, broker_id, super_user_role, tip_verifier, exchange_rate, tip_command, broker_api_key, iex_api_key, coin_market_cap_api_key):
        self.loop = asyncio.get_event_loop()
        self.web = WebWrapper(self.loop)
        self.discord = DiscordWrapper(token, self.web, prefix, connectionString, spamLimit, spamTimeout, display_response_id, broker_id, super_user_role, tip_verifier, exchange_rate, tip_command, broker_api_key, iex_api_key, coin_market_cap_api_key)
        self.discord_task = None
        self.web_task = None
        self.response_checker_task = None
        self.status_updater_task = None
        self.shutdown_error = False
        self.do_shutdown = False
    
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
      
        # make sure the primary loop is interruptable
        for signame in ("SIGINT", "SIGTERM"):
            # windows doesn't have signals, so this will error if running on windows
            try:
                self.loop.add_signal_handler(getattr(signal, signame),functools.partial(begin_shutdown, signame))
            except NotImplementedError:
                _logger.info('Couldn\'t set up signal handler for {}'.format(signame))
                pass

        self.discord_task = ensure_future(self.discord.start())
        self.web_task = ensure_future(self.web.run())
        #self.response_checker_task = ensure_future(self.discord.check_pending_responses())
        
        try:
            self.loop.run_until_complete(self.process())
        except asyncio.CancelledError:
            pass
        
        self.loop.close()
        sys.exit(self.shutdown_error)
    
    def stop(self, is_error=False):
        _logger.info("Stopping OttoBot")
        self.shutdown_error = is_error
        self.do_shutdown = True
        
        if self.discord_task and not self.discord_task.done():
            ensure_future(self.discord.disconnect())
    
    async def process(self):
        #task_list = [self.web_task, self.discord_task, self.response_checker_task]
        task_list = [self.web_task, self.discord_task]
        if self.status_updater_task:
            task_list.append(self.status_updater_task)
        """
        TODO: this was here before. some variant that re-instantiates *just* the discord portion of the app
        should be implemented at some point in the future
        while True:
            _logger.info('about to wait...')
            await asyncio.wait(task_list, return_when=asyncio.FIRST_COMPLETED)
            if self.do_shutdown:
                _logger.info('Shutdown was initiated')
                return
        """

        await asyncio.wait(task_list, return_when=asyncio.FIRST_COMPLETED)


def main():
    globalSettings.init()
    bot = OttoBot(globalSettings.config.get('DEFAULT', 'token'),
            globalSettings.config.get('DEFAULT', 'prefix'),
            globalSettings.config.get('DEFAULT', 'connectionString'),
            int(globalSettings.config.get('DEFAULT', 'spam_limit')),
            int(globalSettings.config.get('DEFAULT', 'spam_timeout')),
            globalSettings.config.get('DEFAULT', 'display_response_id') == 'True',
            globalSettings.config.get('DEFAULT', 'broker_id'),
            globalSettings.config.get('DEFAULT', 'super_user_role'),
            globalSettings.config.get('DEFAULT', 'tip_verifier_id'),
            globalSettings.config.get('DEFAULT', 'exchange_rate'),
            globalSettings.config.get('DEFAULT', 'tip_command'),
            globalSettings.config.get('DEFAULT', 'broker_api_key'),
            globalSettings.config.get('DEFAULT', 'iex_api_key'),
            globalSettings.config.get('DEFAULT', 'coin_market_cap_api_key'))
    bot.start()

main()
