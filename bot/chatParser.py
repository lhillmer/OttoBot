import webWrapper
import json

import logging
from enum import Enum

_logger = logging.getLogger()
_commandsFileJson = "commands.json"

class CommandType(Enum):
    STARTS_WITH = 1
    CONTAINS = 2
    EQUALS = 3

class Command():
    """This represents a command that the bot will respond to"""
    def __init__(self, cmd_type, case_sensitive, removable, to_match, responses):
        if not isinstance(cmd_type, CommandType):
            raise TypeError("cmd_type must be an enum CommandType")
        self.cmd_type = cmd_type
        self.case_sensitive = case_sensitive
        self.removable = removable
        
        if case_sensitive:
            self.to_match = to_match
        else:
            self.to_match = to_match.upper()
        
        self.responses = responses

    def is_text_only(self):
        result = True
        for response in self.responses:
            if not isinstance(response, str):
                result = False
                break

        return result
    
    def does_match(self, input):
        if not self.case_sensitive:
            input = input.upper()
        
        if self.cmd_type is CommandType.STARTS_WITH:
            return input.startswith(self.to_match)
        elif self.cmd_type is CommandType.CONTAINS:
            return self.to_match in input
        elif self.cmd_type is CommandType.EQUALS:
            return self.to_match == input

class CommandEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Command):
            return o.__dict__
        elif isinstance(o, CommandType):
            return o.value
        return json.JSONEncoder.default(self, o)

class CommandDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if 'cmd_type' not in obj:
            return obj
        else:
            return Command(CommandType(int(obj['cmd_type'])),
                    obj['case_sensitive'],
                    obj['removable'],
                    obj['to_match'],
                    obj['responses'])
            

class ChatParser():
    def __init__(self):
                self.commands = []
                self.specialCommands = []
                try:
                    with open(_commandsFileJson, "r") as f:
                        self.commands = json.load(f, cls=CommandDecoder)
                    print("loaded # of commands: " + str(len(self.commands)))
                except Exception as e:
                    print("Couldn't load commands: " + str(e))

                self.add_command(Command(CommandType.STARTS_WITH,
                    False,
                    False,
                    "$add",
                    ["I'm about to add some numbers", add, "That was fun!"]))

                self.add_command(Command(CommandType.STARTS_WITH,
                    False,
                    False,
                    "$createCommand",
                    [create_command]))

                self.add_command(Command(CommandType.STARTS_WITH,
                    False,
                    False,
                    "$deleteCommand",
                    [delete_command]))

                self.add_command(Command(CommandType.EQUALS,
                    False,
                    False,
                    "$watch",
                    [getCrawlLink]))
                
                self.add_command(Command(CommandType.EQUALS,
                    False,
                    False,
                    "$dumpLink",
                    [getCrawlDumpLink]))

                self.add_command(Command(CommandType.EQUALS,
                    False,
                    False,
                    "$list",
                    [list_commands]))
                
    async def get_replies(self, message, web):
        """this yields strings until it has completed its reply"""

        for cmd in self.get_commands():
            if cmd.does_match(message.content):
                _logger.info("Matched %s to command %s", message.content, cmd.to_match)
                for response in cmd.responses:
                    if isinstance(response, str):
                        yield response
                    elif callable(response):
                        yield await response(message, web, self)
                    else:
                        raise TypeError("invalid value in responses: " + str(response))

    def add_command(self, cmd):
        if not isinstance(cmd, Command):
            raise TypeError("cmd must be a Command object")
        
        if not cmd.is_text_only():
            self.specialCommands.append(cmd)
        else:
            self.commands.append(cmd)

    def get_commands(self):
        return self.specialCommands + self.commands

    def save_commands(self):
        _logger.info("starting save!")
        try:
            with open(_commandsFileJson, 'w') as jsonFile:
                json.dump(self.commands, jsonFile, cls=CommandEncoder)
            _logger.info("done!")
        except Exception as e:
            _logger.info("couldn't save commands: " + str(e))



async def add(message, web, parser):
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
    return result

async def create_command(message, web, parser):
    split = message.content.split(" ", 2)
    result = ""

    if split[1] == "Bad to the bone http://momobot.net/cat/TP3.jpg":
        return "Stop it, Max"

    try:
        parser.add_command(Command(CommandType.EQUALS,
                False,
                True,
                split[1],
                [split[2]]))
        result = "Added command: " + split[1]
        parser.save_commands()
    except Exception as e:
        result = "Failed to add command: " + str(e)

    return result

async def delete_command(message, web, parser):
    split = message.content.split(" ")
    result = ""
    for c in parser.commands:
        if c.does_match(split[1]):
            if c.removable:
                parser.commands.remove(c)
                parser.save_commands()
                result = "Removed command: " + c.to_match
                break
            else:
                result = "Command not removable"
                break
    return result

async def getCrawlLink(message, web, parser):
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
    
    return result

async def getCrawlDumpLink(message, web, parser):
    split = message.content.split(" ")
    result = None
    if len(split) == 1:
        result = "You can't watch no one!"
    else:
        if await web.doesCrawlUserExist(split[1]):
            result = "http://crawl.akrasiac.org/rawdata/{}/{}.txt".format(split[1], split[1])
        else:
            result = split[1] + "?? That person doesn't even play crawl!"
    
    return result

async def list_commands(message, web, parser):
    output = "```"
    width = 40
    for cmd in parser.get_commands():
        if len(output) != 0:
            output += "\n"
        output += cmd.to_match + (40 - len(cmd.to_match)) * " "
        if cmd.is_text_only():
            output += " (Text-Only Response)"
        else:
            output += "                     "
        if cmd.removable:
            output += " (Removable)"

    output += "```"

    return output

