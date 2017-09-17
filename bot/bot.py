import chatParser
from postgresWrapper import PostgresWrapper
from functionExecutor import FunctionExecutor

import discord

import datetime
import asyncio
import logging

"""i'm copying a ton of code from here:
    https://github.com/gammafunk/Cerebot/blob/master/cerebot/discord.py
    i totally don't understand most of it
"""

_logger = logging.getLogger()

"""what's the difference between these two?"""
if hasattr(asyncio, "async"):
    ensure_future = asyncio.async
else:
    ensure_future = asyncio.ensure_future

class DiscordWrapper(discord.Client):
    def __init__(self, token, webWrapper, prefix, connectionString, spamLimit, spamTimeout, displayResponseId, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ping_task = None
        self.token = token
        self.db = PostgresWrapper(connectionString)
        self.function_executor = FunctionExecutor()
        self.chat_parser = chatParser.ChatParser(prefix, self.db, self.function_executor)
        self.webWrapper = webWrapper
        self.spam_limit = spamLimit
        self.spam_timeout = spamTimeout
        self.display_response_id = displayResponseId

    async def clear_chat(self, server_id, channel_id):
        for server in self.servers:
            if server.id == server_id:
                for channel in server.channels:
                    if channel.id == channel_id:
                        try:
                            if not channel.permissions_for(server.me).manage_messages:
                                return "OttoBot has insufficient permissions to clear this channel"
                        except Exception as e:
                            _logger.error("Failed to get permissions for clear command. Assuming bot does not have permissions")
                            return "OttoBot has insufficient permissions to clear this channel"
                        def is_not_pinned(m):
                            return not m.pinned
                        await self.purge_from(message.channel, check=is_not_pinned)
                        return "Fresh chat for ya!"
                break
        _logger.error("Could not match server_id (%s) and channel_id (%s)", server_id, channel_id)
        return "Huh, that channel doesn't exist on that server. weird."

    
    def log_exception(self, e, error_msg):
        error_reason = type(e).__name
        if e.args:
            error_reason = "{}: {}".format(error_reason, e.args[0])
        _logger.error("Discord Error: %s: %s", error_msg, error_reason)
    
    """what is the point of this? I'm assuming it's some sort of keep-alive, but idfk bro"""
    async def start_ping(self):
        while True:
            if self.is_closed:
                return
            
            try:
                await self.ws.ping()
            
            except asyncio.CancelledError:
                return
            
            except Exception as e:
                self.log_exception(e, "Unable to send ping")
                ensure_future(self.disconnect())
                return
            
            await asyncio.sleep(10)
            
    
    async def on_message(self, message):
        try:
            if message.server and not message.channel.permissions_for(message.server.me).send_messages:
                return
        except Exception as e:
            _logger.error("Failed to get permissions for bot user. Assuming the bot has permissions")
        
        try:
            if isinstance(message.author, discord.Member):
                reply_generator = self.chat_parser.get_replies(message, self, self.webWrapper, self.db, self.spam_timeout, self.spam_limit, self.display_response_id)
                if reply_generator:
                    async for reply in reply_generator:
                        if not reply:
                            continue
                        await self.handle_reply(message, reply)
        except Exception as e:
            _logger.error("Error handling command: %s", str(e))

    
    """this will probably make sense once I understand ensure_future and start_ping"""
    async def on_ready(self):
        self.ping_task = ensure_future(self.start_ping())
    
    async def start(self):
        await self.login(self.token)
        await self.connect()
    
    async def disconnect(self):
        
        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
        
        try:
            await self.close()
        except Exception as e:
            self.log_exception(e, "Error when disconnecting")
    
    async def handle_reply(self, message, reply):
        if not reply:
            _logger.info("received empty string from yield. continuing...")
        else:
            #max number of chars discord allows in a message
            max_length = 1500
            reply_list = []
            next = reply
            while len(next) > max_length:
                newline = next.rfind('\n')
                if newline == -1:
                    reply_list.append(next[0:max_length])
                    next = next[max_length:]
                else:
                    reply_list.append(next[0:newline])
                    next = next[newline+1:]
            reply_list.append(next)
            for r in reply_list:
                await self.send_message(message.channel, r)
    
    async def check_pending_responses(self):
        _logger.info("Staring pending response checker")
        while True:
            #only check every 15 seconds
            await asyncio.sleep(15)
            try:
                responses = self.db.get_ready_pending_responses()
                for response in responses:
                    request = self.db.get_request(response.request_id)
                    _logger.info("handling pending response (%s) for request (%s) for command (%s)", str(response.id), str(request.id), str(request.command_id))
                    if request.command_id in self.chat_parser.commands:
                        if response.previous_response in self.chat_parser.responses[request.command_id]:
                            prev = self.chat_parser.responses[request.command_id][response.previous_response]
                            async for reply in self.chat_parser.get_responses(request.command_id, prev.next, request.id, response.message, self, self.webWrapper):
                                await self.handle_reply(response.message, reply)
                        else:
                            _logger.warn("previous_response (%s) for request (%s) no longer exists. ignoring", str(response.previous_response), str(request.id))
                    else:
                        _logger.warn("command for request (%s) is no longer active. ignoring", str(request.id))
                    _logger.info("pending response (%s) handled", str(response.id))
                    self.db.delete_pending_response(response.id)
            except Exception as e:
                _logger.error("Ignoring error in check_pending_responses: %s", str(e))
