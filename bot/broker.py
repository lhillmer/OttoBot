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

        self._populate_user_cache()

    @staticmethod
    def is_market_live(time=None):
        if time is None:
            time = datetime.datetime.now(pytz.timezone('EST5EDT'))
        return (time.hour > 9 or (time.hour == 9 and time.minute >= 30)) and time.hour < 16
    
    async def _get_stock_value(self, ticker_symbol):
        if not self.is_market_live():
            #raise Exception('Can\'t trade after hours')
            pass
        response = await self._rest.request('/stock/%s/quote' % ticker_symbol , {})
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
        user_list = self._db.broker_get_all_users()

        for user in user_list:
            self._user_cache[user.id] = user
            self._user_stocks[user.id] = self._load_user_stocks(user.id)
    
    def _update_single_user(self, user_id):
        user = self._db.broker_get_single_user(user_id)
        self._user_cache[user.id] = user
        self._user_stocks[user.id] = self._load_user_stocks(user.id)
    
    def _load_user_stocks(self, user_id):
        stock_list = self._db.broker_get_stocks_by_user(user_id)
        
        # create a dictionary of the stocks, grouped by ticker
        stock_dict = {}
        for stock in stock_list:
            if stock.ticker_symbol in stock_dict:
                stock_dict[stock.ticker_symbol].append(stock)
            else:
                stock_dict[stock.ticker_symbol] = [stock]

        return stock_dict
    
    async def _handle_command(self, request_id, response_id, message, bot, parser, web):
        command_args = message.content.split(' ')
        # assumption, first value in message is '$broker'
        if len(command_args) < 2:
            return ('Specify a broker operation, please', False)
        
        command = command_args[1]
        
        if command == 'register':
            if message.author.id in self._user_cache:
                return ('User {} already exists'.format(self._user_cache[message.author.id].display_name), False)
            self._db.broker_create_user(message.author.id, message.author.name)
            self._update_single_user(message.author.id)
            new_user = self._user_cache[message.author.id]
            return ('Welcome, {}. You have a starting balance of {}'.format(new_user.display_name, new_user.balance), True)
        elif command == 'balance':
            if message.author.id not in self._user_cache:
                return ('Sorry {}, but you don\'t have an account. Create one with `$broker register`'.format(message.author.name), False)
            user = self._user_cache[message.author.id]
            return ('{}, you have a balance of {}'.format(user.display_name, user.balance), True)
        elif command == 'liststocks':
            if message.author.id not in self._user_cache:
                return ('Sorry {}, but you don\'t have an account. Create one with `$broker register`'.format(message.author.name), False)
            user = self._user_cache[message.author.id]
            stock_string = ''
            for symbol in self._user_stocks[user.id]:
                stock_string += '{} {} stocks, '.format(len(self._user_stocks[user.id][symbol]), symbol.upper())
            if stock_string:
                stock_string = stock_string[:-2]
                return ('{}, you have the following stocks: {}'.format(user.display_name, stock_string), True)
            else:
                return ('{}, you have no stocks!'.format(user.display_name), True)

        elif command == 'buystock':
            if message.author.id not in self._user_cache:
                return ('Sorry {}, but you don\'t have an account. Create one with `$broker register`'.format(message.author.name), False)
            if len(command_args) < 4:
                return ('Sorry, you don\'t seem to have enough values in your message for me to parse.', False)
            symbol = command_args[2]
            quantity = command_args[3]
            # make sure we have a valid quantity
            try:
                quantity = int(quantity)
            except Exception:
                return ('No transaction occurred. Couldn\'t convert {} to an int'.format(quantity), False)
            # make sure we can get the cost properly
            try:
                per_stock_cost = await self._get_stock_value(symbol)
            except Exception as e:
                return ('No transaction occurred. Couldn\'t get stock {} value: {}'.format(symbol, e), False)
            
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message.author.id]
            if cur_user.balance < (quantity * per_stock_cost):
                return ('No transaction occurred. Sorry {}, you don\'t have sufficient funds ({}) to buy {} {} stocks at {}'.format(cur_user.display_name,
                    quantity * per_stock_cost, quantity, symbol, per_stock_cost), False)

            # make the transaction, and report success
            result = self._db.broker_buy_regular_stock(cur_user.id, symbol, per_stock_cost, quantity)
            if result is not None:
                # if we succeeded, update the cached user
                self._update_single_user(cur_user.id)
                return ('Congratulations {}, you\'re the proud new owner of {} additional {} stocks'.format(cur_user.display_name, quantity, symbol), True)
            else:
                return ('No transaction occurred. Sorry {}, something went wrong trying to buy the stocks. Go yell at :otto:'.format(cur_user.display_name), False)
        elif command == 'sellstock':
            if message.author.id not in self._user_cache:
                return ('Sorry {}, but you don\'t have an account. Create one with `$broker register`'.format(message.author.name), False)
            if len(command_args) < 4:
                return ('Sorry, you don\'t seem to have enough values in your message for me to parse.', False)
            symbol = command_args[2]
            quantity = command_args[3]
            # make sure we have a valid quantity
            try:
                quantity = int(quantity)
            except Exception:
                return ('No transaction occurred. Couldn\'t convert {} to an int'.format(quantity), False)
            # make sure we can get the cost properly
            try:
                per_stock_cost = await self._get_stock_value(symbol)
            except Exception as e:
                return ('No transaction occurred. Couldn\'t get stock {} value: {}'.format(symbol, e), False)
            
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message.author.id]
            cur_stocks = 0
            if symbol in self._user_stocks[message.author.id]:
                cur_stocks = len(self._user_stocks[message.author.id][symbol])
            if quantity > cur_stocks:
                return ('No transaction occurred. Sorry {}, you only have {} {} stocks'.format(cur_user.display_name, cur_stocks, symbol), False)

            # make the transaction, and report success
            result = self._db.broker_sell_stock(cur_user.id, symbol, per_stock_cost, quantity)
            if result is not None:
                # if we succeeded, update the cached user
                self._update_single_user(cur_user.id)
                cur_user = self._user_cache[message.author.id]
                return ('Congratulations {}, your new balance is {}'.format(cur_user.display_name, cur_user.balance), True)
            else:
                return ('No transaction occurred. Sorry {}, something went wrong trying to sell the stocks. Go yell at :otto:'.format(cur_user.display_name), False)
        else:
            return ('Did not recognize command: ' + command, False)
    
    async def handle_command(self, request_id, response_id, message, bot, parser, web):
        result = await self._handle_command(request_id, response_id, message, bot, parser, web)
        return ("THIS IS IN BETA, ALL RECORDS WILL BE EVENTUALLY WIPED\n" + result[0], result[1])