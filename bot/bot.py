import chatParser

import discord

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
    def __init__(self, token, webWrapper, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ping_task = None
        self.token = token
        self.chat_parser = chatParser.ChatParser()
        self.webWrapper = webWrapper

        #add discord-specific chat commands here
        self.chat_parser.addCommand(
            chatParser.Command(
                chatParser.CommandType.EQUALS,
                False,
                                False,
                "$clear",
                [self.clearChat])
            )

    async def clearChat(self, message, web):
        try:
            if message.server and not message.channel.permissions_for(message.server.me).manage_messages:
                return "OttoBot has insufficient permissions to clear this channel"
        except Exception as e:
            _logger.error("Failed to get permissions for clear command. Assuming bot does not have permissions")
            return "OttoBot has insufficient permissions to clear this channel"

        def is_not_pinned(m):
            return not m.pinned

        await self.purge_from(message.channel, check=is_not_pinned)

        return "Fresh chat for ya!"

    
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
            
        if isinstance(message.author, discord.Member) and self.user != message.author:
            async for reply in self.chat_parser.get_replies(message, self.webWrapper):
                if not reply or len(reply) == 0:
                    _logger.info("received empty string from yield. continuing...")
                    continue
                else:
                    _logger.info("received from yield %s", reply)
                    await self.send_message(message.channel, reply)

    
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
