import webWrapper

import logging
from enum import Enum

_logger = logging.getLogger()

class CommandType(Enum):
	STARTS_WITH = 1
	CONTAINS = 2
	EQUALS = 3

class Command():
	"""This represents a command that the bot will respond to. Eventually, this should be able to hand further more complicated actions. For now, it just matches responses to """
	def __init__(self, cmd_type, case_sensitive, to_match, responses):
		if not isinstance(cmd_type, CommandType):
			raise TypeError("cmd_type must be an enum CommandType")
		self.cmd_type = cmd_type
		self.case_sensitive = case_sensitive
		
		if case_sensitive:
			self.to_match = to_match
		else:
			self.to_match = to_match.upper()
		
		self.responses = responses
	
	def does_match(self, input):
		if  not self.case_sensitive:
			input = input.upper()
		
		if self.cmd_type is CommandType.STARTS_WITH:
			return input.startswith(self.to_match)
		elif self.cmd_type is CommandType.CONTAINS:
			return self.to_match in input
		elif self.cmd_type is CommandType.EQUALS:
			return self.to_match == input

class ChatParser():

	def __init__(self, commands):
		self.commands = commands
	
	async def get_replies(self, message, web):
		"""this yields strings until it has completed its reply"""
		
		for cmd in self.commands:
			if cmd.does_match(message.content):
				_logger.info("Matched %s to command %s", message.content, cmd.to_match)
				for response in cmd.responses:
					if isinstance(response, str):
						yield response
					elif callable(response):
						yield await response(message, web)
					else:
						raise TypeError("invalid value in responses: " + str(response))

	def addCommand(self, cmd):
		if not isinstance(cmd, Command):
			raise TypeError("cmd must be a Command object")
		self.commands.append(cmd)

async def add(message, web):
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

async def getCrawlLink(message, web):
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

async def getCrawlDumpLink(message, web):
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

"""for now, curating the commands, because it's easier that way"""

commands = [
	Command(CommandType.STARTS_WITH,
			False,
			"$hi",
			["Hello, I am OttoBot"]),
	Command(CommandType.STARTS_WITH,
			False,
			"$add",
			["I'm about to try and add some numbers",add, "That was fun!"]),
	Command(CommandType.STARTS_WITH,
			False,
			"$watch",
			[getCrawlLink]),
	Command(CommandType.EQUALS,
			False,
			"$rollout",
			["Fuck you"]),
	Command(CommandType.STARTS_WITH,
			False,
			"$dumpLink",
			[getCrawlDumpLink]),
        Command(CommandType.EQUALS,
                        False,
                        "$stallman",
                        ["Have you tried installing  Free as in Free Speech operating system? Proprietary software may be poisoning your system."])
]
