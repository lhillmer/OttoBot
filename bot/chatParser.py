import logging
from enum import Enum

_logger = logging.getLogger()

class CommandType(Enum):
	STARTS_WITH = 1
	CONTAINS = 2

class Command():
	"""This represents a command that the bot will respond to. Eventually, this should be able to hand further more complicated actions. For now, it just matches responses to """
	def __init__(self, cmd_type, to_match, responses, actions):
		if not isinstance(cmd_type, CommandType):
			raise TypeError("cmd_type must be an enum CommandType")
		self.cmd_type = cmd_type
		self.to_match = to_match
		self.responses = responses
		self.actions = actions
	
	def does_match(self, input):
		if self.cmd_type is CommandType.STARTS_WITH:
			return input.startswith(self.to_match)
		elif self.cmd_type is CommandType.CONTAINS:
			return self.to_match in input

class ChatParser():
	
	async def get_replies(self, message):
		"""this yields strings until it has completed its reply"""
		
		for cmd in commands:
			if cmd.does_match(message.content):
				_logger.info("Matched %s to command %s", message.content, cmd.to_match)
				for response in cmd.responses:
					if isinstance(response, int):
						yield cmd.actions[response](message)
					else:
						yield response

def add(message):
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

"""for now, curating the commands, because it's easier that way"""

commands = [
	Command(CommandType.STARTS_WITH,
			"^hi",
			["Hello, I am OttoBot"],
			[]),
	Command(CommandType.CONTAINS,
			"Otto",
			["Did you mean me?", "No, you probably wanted OttoTonsorialist", "It's ok, I'll go"],
			[]),
	Command(CommandType.STARTS_WITH,
			"^add",
			["I'm about to try and add some numbers",0, "That was fun!"],
			[add]),
]
