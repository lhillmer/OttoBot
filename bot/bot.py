import chatParser
from postgresWrapper import PostgresWrapper
from functionExecutor import FunctionExecutor
from cryptoConverter import CryptoConverter
from broker import OttoBroker
from stockInfo import StockInfo

import discord

import datetime
import asyncio
import logging
import traceback

"""
i'm copying a ton of code from here:
https://github.com/gammafunk/Cerebot/blob/master/cerebot/discord.py
"""

_logger = logging.getLogger()

ensure_future = asyncio.ensure_future

class DiscordWrapper(discord.Client):
    def __init__(self, token, webWrapper, prefix, connectionString, spamLimit, spamTimeout, displayResponseId,
            broker_id, super_user_role, tip_verifier, exchange_rate, tip_command, broker_api_key, iex_api_key,
            coin_market_cap_api_key, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ping_task = None
        self.token = token
        self.db = PostgresWrapper(connectionString)
        self._broker = OttoBroker(webWrapper, self.db, broker_id, super_user_role, tip_verifier, exchange_rate, tip_command, broker_api_key)
        self.function_executor = FunctionExecutor(self._broker)
        self.chat_parser = chatParser.ChatParser(prefix, self.db, self.function_executor)
        self.webWrapper = webWrapper
        self.spam_limit = spamLimit
        self.spam_timeout = spamTimeout
        self.display_response_id = displayResponseId
        #hardcoding because lazy
        self.status_frequency = 60
        self.crypto = CryptoConverter(self.webWrapper, coin_market_cap_api_key)
        self.ping_retry_max = 10
        self.ping_retry_count = self.ping_retry_max
        self._iex_api_key = iex_api_key
    
    def get_stock_info_object(self, web_wrapper):
        return StockInfo(web_wrapper, self._iex_api_key)

    async def clear_chat(self, server_id, channel_id):
        for server in self.servers:
            if server.id == server_id:
                for channel in server.channels:
                    if channel.id == channel_id:
                        try:
                            if not channel.permissions_for(server.me).manage_messages:
                                return "OttoBot has insufficient permissions to clear this channel"
                        except Exception:
                            _logger.error("Failed to get permissions for clear command. Assuming bot does not have permissions")
                            return "OttoBot has insufficient permissions to clear this channel"
                        def is_not_pinned(m):
                            return not m.pinned
                        await self.purge_from(channel_id, check=is_not_pinned)
                        return "Fresh chat for ya!"
                break
        _logger.error("Could not match server_id (%s) and channel_id (%s)", server_id, channel_id)
        return "Huh, that channel doesn't exist on that server. weird."

    
    def log_exception(self, error_msg):
        _logger.error("Discord Error: %s", error_msg)
    
    async def on_message(self, message):
        try:
            if message.server and not message.channel.permissions_for(message.server.me).send_messages:
                return
        except Exception as e:
            # _logger.warning("Failed to get permissions for bot user. Assuming the bot has permissions")
            pass
        
        try:
            reply_generator = self.chat_parser.get_replies(message, self, self.webWrapper, self.db, self.spam_timeout, self.spam_limit, self.display_response_id)
            if reply_generator:
                async for reply in reply_generator:
                    if not reply:
                        continue
                    await self.handle_reply(message, reply)
            
            tip_result = await self._broker.check_for_tips(message)
            if tip_result:
                await self.handle_reply(message, tip_result)

        except Exception as e:
            _logger.error('Exception trying to handle message')
            _logger.exception(e)
            await self.send_message(message.channel, 'Ya dun fucked up (Exception: {})'.format(e))

    
    async def start(self):
        await self.login(self.token)
        await self.connect()
    
    async def disconnect(self):
        _logger.debug('Disconnect called...')
        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
        try:
            await self.close()
        except Exception:
            self.log_exception("Error when disconnecting")
    
    async def handle_reply(self, message, reply, image=None):
        if not reply:
            _logger.info("received empty string from yield. continuing...")
        else:
            #max number of chars discord allows in a message
            max_length = 1500
            reply_list = []
            next_reply = reply
            while len(next_reply) > max_length:
                newline = next_reply.rfind('\n')
                if newline == -1:
                    reply_list.append(next_reply[0:max_length])
                    next_reply = next_reply[max_length:]
                else:
                    reply_list.append(next_reply[0:newline])
                    next_reply = next_reply[newline+1:]
            reply_list.append(next_reply)
            for idx, r in enumerate(reply_list):
                if image is not None and idx == 0:
                    image = discord.File(image)
                await message.channel.send(r, file=image)
    
    async def check_pending_responses(self):
        # _logger.info("Staring pending response checker")
        while True:
            #only check every 5 seconds
            await asyncio.sleep(5)
            try:
                responses = self.db.get_ready_pending_responses()
                for response in responses:
                    request = self.db.get_request(response.request_id)
                    # _logger.info("handling pending response (%s) for request (%s) for command (%s)", str(response.id), str(request.id), str(request.command_id))
                    if request.command_id in self.chat_parser.commands:
                        if response.next_response in self.chat_parser.responses[request.command_id]:
                            async for reply in self.chat_parser.get_responses(request.command_id, response.next_response, request.id, response.message, self, self.webWrapper, self.display_response_id, 1):
                                await self.handle_reply(response.message, reply)
                        else:
                            # _logger.warn("response (%s) for request (%s) no longer exists. ignoring", str(response.next_response), str(request.id))
                            pass
                    else:
                        # _logger.warn("command for request (%s) is no longer active. ignoring", str(request.id))
                        pass
                    # _logger.info("pending response (%s) handled", str(response.id))
                    self.db.delete_pending_response(response.id)
            except Exception as e:
                # _logger.error("Ignoring error in check_pending_responses: %s", str(e))
                # _logger.exception(e)
                pass
