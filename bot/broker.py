from webWrapper import RestWrapper

import json
import logging
import datetime
import pytz
import copy

_logger = logging.getLogger()

class OttoBroker():
    def __init__(self, webWrapper, db):
        self._rest = RestWrapper(webWrapper,
            "https://api.iextrading.com/1.0", {})
        self._quote_value_key = 'latestPrice'
        self._db = db
        self._user_cache = {}
        self._user_stocks = {}

    @staticmethod
    def is_market_live(time=None):
        if time is None:
            time = datetime.datetime.now(pytz.timezone('EST5EDT'))
        return (time.hour > 9 or (time.hour == 9 and time.minute >= 30)) and time.hour < 16
    
    async def _get_stock_value(self, ticker_symbol):
        if not self.is_market_live():
            raise Exception('Can\'t trade after hours')
        response = await self.rest.request('/stock/%s/quote' % symbol , {})
        unparsed = await response.text()
        data = None
        try:
            data = json.loads(unparsed)
        except Exception:
            raise Exception('Failed to convert api result to json')
        if data is None:
            raise Exception('Got None from api response')
        elif not isinstance(data, dict):
            raise Exception('Unexpected data type ' + str(type(data)))
        elif self._quote_value_key not in data:
            raise Exception('Key {} was not in response from api'.format(self._quote_value_key))
        
        result = data[self._quote_value_key]
        if not isinstance(result, float):
            try:
                result = float(result)
            except Exception:
                raise Exception('Failed to convert stock value {} to a float')
        return result
    
    def _populate_user_cache(self):
        self._user_cache = {}
        # get users from db
        user_list = []

        for user in user_list:
            self._user_cache[user.id] = user
            self._user_stocks[user.id] = self._load_user_stocks(user.id)
    
    def _update_single_user(self, user_id):
        # get user from id
        user = None
        self._user_cache[user.id] = user
        self._user_stocks[user.id] = self._load_user_stocks(user.id)
    
    def _load_user_stocks(self, user_id):
        # get stocks from user by id
        stock_list = []
        return stock_list
    
    async def _handle_command(self, request_id, response_id, message, bot, parser, web):
        command_args = message.content.split(' ')
        # assumption, first value in message is '$broker'
        if len(command_args) < 1:
            return ('Specify a broker operation, please', False)
        
        command = command_args[1]
        
        if command == 'register':
            if message.author.id in self._user_cache:
                return ('User {} already exists'.format(self._user_cache[message.author.id].display_name))
            self._db.create_user(message.author.id, message.author.name)
            self._update_single_user(message.author.id)
            new_user = self._user_cache[message.author.id]
            return ('Welcome, {}. You have a starting balance of {.2f}'.format(new_user.display_name, new_user.balance))
        elif command == 'buystock':
            if message.author.id not in self._user_cache:
                return ('Sorry {}, but you don\'t have an account. Create one with `$broker register`'.format(message.author.name), False)
            if len(command_args) < 4:
                return ('Sorry, you don\'t seem to have enough values there for me to parse.')
            symbol = command_args[3]
            quantity = command_args[4]
            # make sure we have a valid quantity
            try:
                quantity = int(quantity)
            except Exception:
                return ('No transaction occurred. Couldn\'t convert {} to an int'.format(quantity))
            # make sure we can get the cost properly
            try:
                per_stock_cost = await self._get_stock_value(symbol)
            except Exception, e:
                return ('No transaction occurred. Couldn\'t get stock {} value: {}'.format(symbol, e))
            
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message.author.id]
            if cur_user.balance < (quantity * per_stock_cost):
                return ('No transaction occurred. Sorry {}, you don\'t have sufficient funds ({.2f}) to buy {} {} stocks at {.2f}'.format(cur_user.display_name,
                    quantity * per_stock_cost, quantity, symbol, per_stock_cost), False)

            # make the transaction, and report success
            result = self.db.buy_regular_stock(cur_user.id, symbol, per_stock_cost, quantity)
            if result is not None:
                # if we succeeded, update the cached user
                self._update_single_user(cur_user.id)
                return ('Congratulations {}, you\'re the proud new owner of {} additional {} stocks'.format(cur_user.display_name, quantity, symbol), True)
            else:
                return ('No transaction occurred. Sorry {}, something went wrong trying to buy the stocks. Go yell at :otto:'.format(cur_user.display_name))
        elif command == 'sellstock':
            if message.author.id not in self._user_cache:
                return ('Sorry {}, but you don\'t have an account. Create one with `$broker register`'.format(message.author.name), False)
            if len(command_args) < 4:
                return ('Sorry, you don\'t seem to have enough values there for me to parse.')
            symbol = command_args[3]
            quantity = command_args[4]
            # make sure we have a valid quantity
            try:
                quantity = int(quantity)
            except Exception:
                return ('No transaction occurred. Couldn\'t convert {} to an int'.format(quantity))
            # make sure we can get the cost properly
            try:
                per_stock_cost = await self._get_stock_value(symbol)
            except Exception, e:
                return ('No transaction occurred. Couldn\'t get stock {} value: {}'.format(symbol, e))
            
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message.author.id]
            cur_stocks = self._user_stocks[message.author.id]
            if symbol not in cur_stocks or quantity > cur_stocks[symbol]:
                return ('No transaction occurred. Sorry {}, you only have {} {} stocks'.format(cur_user.display_name, quantity, symbol), False)

            # make the transaction, and report success
            result = self.db.sell_stock(cur_user.id, symbol, per_stock_cost, quantity)
            if result is not None:
                # if we succeeded, update the cached user
                self._update_single_user(cur_user.id)
                return ('Congratulations {}, your new balance is {.2f}'.format(cur_user.display_name, cur_user.balance), True)
            else:
                return ('No transaction occurred. Sorry {}, something went wrong trying to sell the stocks. Go yell at :otto:'.format(cur_user.display_name))
        else:
            return ('Did not recognize command: ' + command, False)
    
    async def handle_command(self, request_id, response_id, message, bot, parser, web):
        result = await self._handle_command(request_id, response_id, message, bot, parser, web)
        return ("THIS IS IN BETA, ALL RECORDS WILL BE EVENTUALLY WIPED\n" + result[0], result[1])