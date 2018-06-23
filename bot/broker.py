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

        self._command_mapping = {
            'register': self._handle_register,
            'balance': self._handle_balance,
            'liststocks': self._handle_list_stocks,
            'buystock': self._handle_buy_stock,
            'sellstock': self._handle_sell_stock
        }

        self._populate_user_cache()

    @staticmethod
    def is_market_live(time=None):
        if time is None:
            time = datetime.datetime.now(pytz.timezone('EST5EDT'))
        return (time.hour > 9 or (time.hour == 9 and time.minute >= 30)) and time.hour < 16
    
    @staticmethod
    def _get_int(string):
        """
        This exists only to provide a nicer error message when converting ints. Allows for a more
        streamlined calling structure
        """
        try:
            return int(string)
        except Exception:
            raise Exception('Couldn\'t convert {} to an integer'.format(string))
    
    async def _get_stock_value(self, ticker_symbol):
        try:
            if not self.is_market_live():
                #raise Exception('Can\'t trade after hours')
                pass
            response = await self._rest.request('/stock/%s/quote' % ticker_symbol , {})
            unparsed = await response.text()
            data = None
            try:
                data = json.loads(unparsed)
            except Exception:
                raise Exception('Invalid API response: {}'.format(unparsed))
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
        except Exception as e:
            raise Exception('Couldn\'t get stock value: {}'.format(str(e)))
    
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

    def _get_user(self, user_id):
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        else:
            raise Exception('You dn\'t have an account. Create one with `$broker register`')
    
    async def _buy_regular_stock(self, user_id, user_display_name, symbol, per_stock_cost, quantity):
        # make the transaction, and report success
        result = self._db.broker_buy_regular_stock(user_id, symbol, per_stock_cost, quantity)
        if result is not None:
            # if we succeeded, update the cached user
            self._update_single_user(user_id)
            return 'Congratulations {}, you\'re the proud new owner of {} additional {} stocks'.format(user_display_name, quantity, symbol)
        raise Exception('Sorry {}, something went wrong in the database. Go yell at :otto:'.format(user_display_name))
    
    async def _handle_buy_stock(self, command_args, message_author):
        try:
            user = self._get_user(message_author.id)
            if len(command_args) < 4:
                raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
            symbol = command_args[2].upper()
            quantity = self._get_int(command_args[3])
            per_stock_cost = await self._get_stock_value(symbol)
            
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message_author.id]
            if cur_user.balance < (quantity * per_stock_cost):
                raise Exception('Sorry {}, you don\'t have sufficient funds ({}) to buy {} {} stocks at {}'.format(cur_user.display_name,
                    quantity * per_stock_cost, quantity, symbol, per_stock_cost))

            return (await self._buy_regular_stock(cur_user.id, cur_user.display_name, symbol, per_stock_cost, quantity), True)
        except Exception as e:
            return ('No transaction occured. {}'.format(str(e)), False)
    
    async def _sell_regular_stock(self, user_id, user_display_name, symbol, per_stock_cost, quantity):
        result = self._db.broker_sell_stock(user_id, symbol, per_stock_cost, quantity)
        if result is not None:
            # if we succeeded, update the cached user
            self._update_single_user(user_id)
            cur_user = self._user_cache[user_id]
            return 'Congratulations {}, your new balance is {}'.format(user_display_name, cur_user.balance)
        raise Exception('No transaction occurred. Sorry {}, something went wrong trying to sell the stocks. Go yell at :otto:'.format(user_display_name))

    async def _handle_sell_stock(self, command_args, message_author):
        try:
            user = self._get_user(message_author.id)
            if len(command_args) < 4:
                return ('Sorry, you don\'t seem to have enough values in your message for me to parse.', False)
            symbol = command_args[2].upper()
            quantity = self._get_int(command_args[3])
            per_stock_cost = await self._get_stock_value(symbol)
            
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message_author.id]
            cur_stocks = 0
            if symbol in self._user_stocks[message_author.id]:
                cur_stocks = len(self._user_stocks[message_author.id][symbol])
            if quantity > cur_stocks:
                raise Exception('Sorry {}, you only have {} {} stocks'.format(cur_user.display_name, cur_stocks, symbol))

            return (await self._sell_regular_stock(cur_user.id, cur_user.display_name, symbol, per_stock_cost, quantity), True)
        except Exception as e:
            return ('No transaction occurred. {}'.format(str(e)), False)

    async def _handle_list_stocks(self, command_args, message_author):
        try:
            user = self._get_user(message_author.id)
            stock_string = ''
            for symbol in self._user_stocks[user.id]:
                stock_string += '{} {} stocks, '.format(len(self._user_stocks[user.id][symbol]), symbol.upper())
            if stock_string:
                stock_string = stock_string[:-2]
                return ('{}, you have the following stocks: {}'.format(user.display_name, stock_string), True)
            else:
                return ('{}, you have no stocks!'.format(user.display_name), True)
        except Exception as e:
            return ('Could not list stocks: {}'.format(str(e)), False)
    
    async def _handle_register(self, command_args, message_author):
        if message_author.id in self._user_cache:
            return ('User {} already exists'.format(self._user_cache[message_author.id].display_name), False)
        self._db.broker_create_user(message_author.id, message_author.name)
        self._update_single_user(message_author.id)
        new_user = self._user_cache[message_author.id]
        return ('Welcome, {}. You have a starting balance of {}'.format(new_user.display_name, new_user.balance), True)
    
    async def _handle_balance(self, command_args, message_author):
        try:
            user = self._get_user(message_author.id)
            return ('{}, you have a balance of {}'.format(user.display_name, user.balance), True)
        except Exception as e:
            return ('Could not report balance: {}'.format(str(e)), False)
    
    async def handle_command(self, request_id, response_id, message, bot, parser, web):
        command_args = message.content.split(' ')
        # assumption, first value in message is '$broker'
        if len(command_args) < 2:
            return ('Specify a broker operation, please', False)
        
        command = command_args[1]

        if command in self._command_mapping:
            result = await self._command_mapping[command](command_args, message.author)
            return ("THIS IS IN BETA, ALL RECORDS WILL BE EVENTUALLY WIPED\n" + result[0], result[1])
        else:
            return ('Did not recognize command: ' + command, False)
