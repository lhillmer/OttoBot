from customSearchEngine import CustomSearchEngine
from stockInfo import StockInfo
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
    def __init__(self, broker):
        self.crypto_symbols = []
        self._broker = broker

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

    async def favorite(self, request_id, response_id, message, bot, parser, web):
        requests = bot.db.get_user_requests(message.author.name)
        counts = {}
        fav_count = 0
        fav_list = []
        for r in requests:
            if r.command_id in counts:
                counts[r.command_id] += 1
            else:
                counts[r.command_id] = 1
            if r.command_id in parser.commands \
                and parser.commands[r.command_id].text != parser.prefix + 'createCommand' \
                and parser.commands[r.command_id].text != parser.prefix + 'deleteCommand' \
                and parser.commands[r.command_id].text != parser.prefix + 'deleteResponse':
                if counts[r.command_id] == fav_count:
                    fav_list.append(r.command_id)
                elif counts[r.command_id] > fav_count:
                    fav_list = [r.command_id]
                    fav_count = counts[r.command_id]
        
        if len(fav_list) > 1:
            result = message.author.mention + ", your favorite commands are: {0} ({1} calls each)"
        else:
            result = message.author.mention + ", your favorite command is: {0} ({1} calls)"

        result = result.format(", ".join(parser.commands[cmd_id].text for cmd_id in fav_list), fav_count)
        return (result, True)

    async def create_command(self, request_id, response_id, message, bot, parser, web):
        _logger.info("test")
        _logger.info(str(message.content))
        split = message.content.split(" ", 2)
        result = ""

        try:
            type_id = parser.get_command_type_id('EQUALS')
            # TODO bad hardcoded check...but i'm leaving it for now because *fast*
            if len(split[2]) > 256:
                raise Exception('Length must be shorter than 256 character')
            newCommand = dataContainers.Command([-1, split[1], True, False, True, type_id])
            newResponse = dataContainers.Response([-1, split[2], None, None, None, -1])
            if newResponse.text.startswith('!tip'):
                raise Exception("I'm just a poor :ottoBot: trying to scrape together a living. No need to steal my momocoins")
            parser.add_command(newCommand, newResponse)
            result = "Added command: " + newCommand.text
        except Exception as e:
            result = "Failed to add command: " + str(e)

        return (result, True)


    async def create_delayed_command(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ", 2)
        result = "Roger roger"

        try:
            cmd_id = parser.get_response_by_id(response_id).command_id
            resp_id = [x for x in parser.responses[cmd_id] if parser.responses[cmd_id][x].text == split[2]]
            if len(resp_id) == 0:
                resp = dataContainers.Response([-1, split[2], None, response_id, None, cmd_id])
                parser.add_command(parser.commands[cmd_id], resp)
                resp_id = [x for x in parser.responses[cmd_id] if parser.responses[cmd_id][x].text == split[2]][0]
            else:
                resp_id = resp_id[0]
            delay = float(split[1])
            
            when = datetime.datetime.now() + datetime.timedelta(seconds=delay)
            new_id = bot.db.insert_pending_response(request_id, resp_id, when, message)
            result += " - " + str(new_id)
        except Exception as e:
            result = "Failed to parse delayed response: " + str(e)
            _logger.error("Failed to create delayed command: {}".format(e))
            _logger.exception(e)

        return (result, False)
    
    async def delete_pending_response(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = ""
    
        if len(split) < 2:
            result = "Please supply a pending response id"
        else:
            try:
                delayed_id = int(split[1])
                bot.db.delete_pending_response(delayed_id)
                result = "Da-Cheated"
            except Exception:
                result = "Failed to parse delayed response id"

        return (result, True)



    async def delete_command(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = "No matching command found"
        for c in parser.commands:
            if parser.is_match(parser.commands[c], split[1]):
                index = 0
                if len(split) > 2:
                    try:
                        index = int(split[2])
                    except Exception:
                        result = split[2] + " is not a valid index"
                        break
                if parser.commands[c].removable:
                    response = parser.get_response(parser.commands[c].id, index)
                    if response:
                        parser.delete_response(response)
                        result = "Removed command: " + parser.commands[c].text
                    else:
                        result = "This command doesn't have that many responses"
                    break
                else:
                    result = "Command not removable"
                    break
        return (result, True)

    async def delete_response(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = "Invalid response"
        try:
            response_id = int(split[1])
            response = parser.get_response_by_id(response_id)
            if response:
                if parser.commands[response.command_id].removable:
                    parser.delete_response(response)
                    result = "Response deleted"
                else:
                    result = "That response is not editable"
            else:
                result = "Could not find matching response"
             
        except Exception:
            result = "Could not parse response id"

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
        output = ', '.join(parser.commands[cmd].text for cmd in sorted(parser.commands, key=lambda x:parser.commands[x].text) if parser.commands[cmd].text.startswith(parser.prefix))
        return (output, True)


    async def find_steam_game(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ", 1)
        result = ""
        if len(split) == 1:
            result = "Please specify a game"
        else:
            cse = CustomSearchEngine(web,
                    globalSettings.config.get('DEFAULT', 'cse_cx_steam'),
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


    async def find_xkcd_comic(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ", 1)
        result = ""
        if len(split) == 1:
            result = "Please specify a keyword"
        else:
            cse = CustomSearchEngine(web,
                    globalSettings.config.get('DEFAULT', 'cse_cx_xkcd'),
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
        false_start = random.randint(1, 10)
        if false_start <= 1:
            return (message.author.mention + " TIMING!!!!!!!!!!!!\n\n\nWait no...", False)
        minTime = 0
        maxTime = 10520000
        delay = random.randrange(minTime, maxTime, 1)
        when = datetime.datetime.now() + datetime.timedelta(seconds=delay)
        next_id = parser.get_response_by_id(response_id).next
        bot.db.insert_pending_response(request_id, next_id, when, message)
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

    async def crypto_data(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        if len(split) < 2:
            result = "No Symbol provided"
        else:
            symbol = split[1]
            result = "Crypto Data ({}):\n".format(symbol)
            try:
                symbol_data = await bot.crypto.get_info(symbol)
            except Exception as e:
                symbol_data = str(e)

            if isinstance(symbol_data, dict):
                prefix_len = max([len(x) for x in symbol_data])
                result += '\n'.join(["`" + str(x).ljust(prefix_len) + ": " + str(symbol_data[x]) + "`" for x in symbol_data])
            else:
                result = "An error occurred getting crypto data: {}".format(symbol_data)
        
        return (result, True)
    
    async def broker(self, request_id, response_id, message, bot, parser, web):
        return await self._broker.handle_command(request_id, response_id, message, bot, parser, web)
    
    async def stock_data(self, request_id, response_id, message, bot, parser, web):
        split = message.content.split(" ")
        result = "Stock Data (%s, %s):\n"
        symbol = None
        symbol_data = None
        error_info = None
        stock_info = bot.get_stock_info_object(web)

        if len(split) > 1:
            symbol = split[1].upper()
            # default to 'live' timing
            timing = 'live'
            duration = -1
            debug = False
            if len(split) > 2:
                timing = split[2].lower()
                if len(split) > 3:
                    extra = split[3:]
                    if 'debug' in extra:
                        debug = True
                    for s in extra:
                        if s.isdigit():
                            duration = int(s)
                            break
                
            try:
                symbol_data = {}
                result = result % (symbol, timing)
                if timing == 'live':
                    symbol_data = await stock_info.live(symbol, debug)
                elif timing == 'daily':
                    symbol_data = await stock_info.daily(symbol, debug)
                elif timing == 'duration':
                    symbol_data = await stock_info.duration(symbol, duration, debug)
                elif timing == 'moving_average':
                    symbol_data = await stock_info.moving_average(symbol, duration, debug)
            except Exception as e:
                error_info = str(e)
        if isinstance(symbol_data, dict):
            _logger.info('something is weird here: {}'.format(symbol_data))
            prefix_len = max([len(x) for x in symbol_data])
            result += '\n'.join(["`" + str(x).ljust(prefix_len) + ": " + str(symbol_data[x]) + "`" for x in symbol_data])
        else:
            result += symbol_data
            
        if error_info is not None:
            result = error_info
        
        return (result, True)
        