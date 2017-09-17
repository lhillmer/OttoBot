from customSearchEngine import CustomSearchEngine
import dataContainers
import globalSettings

import datetime
import random
import logging

_logger = logging.getLogger()

#This class is mainly a way to keep the code clean
#So any functions required purely for command execution go here
#This also will facilitate the execution of pending responses
#which don't naturally have a context in the chat parser anymore
class FunctionExecutor():
    def execute(self, function, request_id, response_id, message, bot, parser, web):
        return getattr(self, function)(request_id, response_id, message, bot, parser, web)

    async def add(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = None
        total = 0
        for i in range(1, len(split)):
            try:
                total += int(split[i])
            except ValueError:
                result = "I can only add numbers, bub"
                break
            except Exception:
                result = "I don't even know what's going on anymore"
                break
        if not result:
            result = "I know, the answer is {}!".format(str(total))
        return (result, True)


    async def create_command(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ", 2)
        result = ""

        if split[1] == "Bad to the bone http://momobot.net/cat/TP3.jpg":
            return "Stop it, Max"

        try:
            type_id = parser.get_command_type_id('EQUALS')
            newCommand = dataContainers.Command([-1, split[1], True, False, True, type_id])
            newResponse = dataContainers.Response([-1, split[2], None, None, None, -1])
            parser.add_command(newCommand, newResponse)
            result = "Added command: " + newCommand.text
        except Exception as e:
            result = "Failed to add command: " + str(e)

        return (result, True)


    async def delete_command(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = "No matching command found"
        for c in parser.commands:
            if parser.is_match(parser.commands[c], split[1]):
                if parser.commands[c].removable:
                    result = "Removed command: " + parser.commands[c].text
                    response = parser.get_first_response(parser.commands[c].id)
                    parser.delete_response(response)
                    break
                else:
                    result = "Command not removable"
                    break
        return (result, True)


    async def get_crawl_link(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = None
        if len(split) == 1:
            result = "You can't watch no one!"
        else:
            _logger.info("about to test for existence of crawl user: " + split[1])
            exists = await web.doesCrawlUserExist(split[1])
            _logger.info("crawl user " + split[1] + " exists: " + str(exists))
            if exists:
                result = "http://crawl.akrasiac.org:8080/#watch-" + split[1]
            else:
                result = split[1] + "?? That person doesn't even play crawl!"

        return (result, True)


    async def get_crawl_dump_link(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = None
        if len(split) == 1:
            result = "You can't watch no one!"
        else:
            if await web.doesCrawlUserExist(split[1]):
                result = "http://crawl.akrasiac.org/rawdata/{}/{}.txt".format(split[1], split[1])
            else:
                result = split[1] + "?? That person doesn't even play crawl!"

        return (result, True)


    async def list_commands(self, request_id, response_id, message, bot, parser, web):
        output = ', '.join(parser.commands[cmd].text if parser.commands[cmd].text.startswith(parser.prefix) for cmd in sorted(parser.commands, key=lambda x:x.text))
        return (output, True)


    async def find_steam_game(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ", 1)
        result = ""
        if len(split) == 1:
            result = "Please specify a game"
        else:
            cse = CustomSearchEngine(web,
                    globalSettings.config.get('DEFAULT', 'cse_cx'),
                    globalSettings.config.get('DEFAULT', 'cse_key'))

            response = await cse.search(split[1])
            if response.status != 200:
                if response.error_message:
                    result = response.error_message + " "
                result += "(Http status: " + str(response.status) + ")"
            elif len(response.items) == 0:
                result = "Found no responses for query"
            else:
                result = response.items[0].title + ": " + response.items[0].link

        return (result, True)


    async def timing_queue(self, request_id, response_id, message, bot, parser, web):
        minTime = 0
        maxTime = 10520000
        delay = random.randrange(minTime, maxTime, 1)
        when = datetime.datetime.now() + datetime.timedelta(seconds=delay)
        bot.db.insert_pending_response(request_id, response_id, when, message)
        return ("Want to know the secret to good comedy?", False)

    async def timing_pop(self, request_id, response_id, message, bot, parser, web):
        return (message.author.mention + " TIMING!!!!!!!!!!!", True)

    async def clear_chat(self, request_id, response_id, message, bot, parser, web):
        if message.server:
            server_id = message.server.id
            channel_id = message.channel.id
            return (await bot.clear_chat(server_id, channel_id), True)
        else:
            return ("Couldn't find server id? I don't really support PMs", False)
