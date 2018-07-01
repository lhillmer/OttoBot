from webWrapper import RestWrapper

import json
import logging
import datetime
import pytz
import copy
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

_logger = logging.getLogger()

class OttoBroker():
    def __init__(self, webWrapper, db, broker_id, tip_verifier, exchange_rate, tip_command):
        self._rest = RestWrapper(webWrapper,
            "https://api.iextrading.com/1.0", {})
        self._db = db
        self._user_cache = {}
        self._user_stocks = {}
        self._tip_verifier = tip_verifier
        self._exchange_rate = Decimal(exchange_rate)
        self._broker_id = broker_id
        self._tip_command = tip_command

        self._command_mapping = {
            'register': self._handle_register,
            'balance': self._handle_balance,
            'liststocks': self._handle_list_stocks,
            'buystock': self._handle_buy_stock,
            'sellstock': self._handle_sell_stock,
            'withdraw': self._handle_withdraw_command
        }

        self._populate_user_cache()

    @staticmethod
    def is_market_live(time=None):
        if time is None:
            time = datetime.datetime.now(pytz.timezone('EST5EDT'))
        
        return (time.weekday() < 5) and ((time.hour > 9 or (time.hour == 9 and time.minute >= 30)) and time.hour < 16)
    
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
    
    async def _get_stock_value(self, symbol_list):
        try:
            response = await self._rest.request('/stock/market/batch/', {'types': 'quote', 'symbols': ','.join(symbol_list)})
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

            unknown_symbols = []
            known_symbols = {}
            try:
                for symbol in symbol_list:
                    if symbol not in data:
                        unknown_symbols.append(symbol)
                    else:
                        known_symbols[symbol] = data[symbol]['quote']['latestPrice']
            except Exception:
                raise Exception('Unexpected response format')
            
            if not len(known_symbols):
                raise Exception('Couldn\'t find values for symbols: {}'.format(unknown_symbols))
            
            mistyped_symbols = {}
            for symbol in known_symbols:
                if not isinstance(known_symbols[symbol], Decimal):
                    try:
                        known_symbols[symbol] = Decimal(known_symbols[symbol])
                    except Exception:
                        mistyped_symbols[symbol] = known_symbols[symbol]
                        del known_symbols[symbol]
            
            if not len(known_symbols):
                error_message = ''
                if unknown_symbols:
                    error_message += 'Couldn\'t find values for symbols: {}'.format(unknown_symbols)
                if mistyped_symbols:
                    if error_message:
                        error_message += '. '
                    error_message += 'Couldn\'t find types for: {}'.format(
                        ','.join(
                            [':'.join([k, mistyped_symbols[k]]) for k in mistyped_symbols]
                        )
                    )
                raise Exception(error_message)

            return known_symbols, unknown_symbols, mistyped_symbols
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
        if not self.is_market_live():
            raise Exception('Can\'t trade after hours')
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
            # here, since there's only one value, we can assume that if there was no exception, we got the value
            stock_vals, _, _ = await self._get_stock_value([symbol])
            per_stock_cost = stock_vals[symbol]
            
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message_author.id]
            if cur_user.balance < (quantity * per_stock_cost):
                raise Exception('Sorry {}, you don\'t have sufficient funds ({}) to buy {} {} stocks at {}'.format(cur_user.display_name,
                    quantity * per_stock_cost, quantity, symbol, per_stock_cost))

            return (await self._buy_regular_stock(cur_user.id, cur_user.display_name, symbol, per_stock_cost, quantity), True)
        except Exception as e:
            return ('No transaction occured. {}'.format(str(e)), False)
    
    async def _sell_regular_stock(self, user_id, user_display_name, symbol, per_stock_cost, quantity):
        if not self.is_market_live():
            raise Exception('Can\'t trade after hours')
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
            # here, since there's only one value, we can assume that if there was no exception, we got the value
            stock_vals, _, _ = await self._get_stock_value([symbol])
            per_stock_cost = stock_vals[symbol]
            
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

            result_lines = [
                ['Capital', user.balance, '']
            ]
            errors = []
            total = user.balance

            stock_counts = {}
            stock_symbols = []
            for stock in self._user_stocks[user.id]:
                stock_symbols.append(stock)
                stock_counts[stock] = len(self._user_stocks[user.id][stock])
            if stock_symbols:
                stock_vals, unknown_vals, mistyped_vals = await self._get_stock_value(stock_symbols)

                if unknown_vals:
                    errors.append('The following stocks had unknown values: {}'.format(unknown_vals))
                
                if mistyped_vals:
                    errors.append('The following stock values could not be converted: {}'.format(mistyped_vals))
                
                for stock in stock_vals:
                    full_stock_value = stock_vals[stock] * stock_counts[stock]
                    full_stock_value = Decimal(full_stock_value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
                    total += full_stock_value

                    purchase_stock_value = Decimal(0)
                    for owned_stock in self._user_stocks[user.id][stock]:
                        purchase_stock_value += owned_stock.purchase_cost
                    
                    result_lines.append([
                        str(stock_counts[stock]) + ' ' + stock,
                        full_stock_value,
                        (Decimal(100) * (full_stock_value - purchase_stock_value) / purchase_stock_value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                    ])

            result_lines.append(['Total', total, ''])

            if errors:
                result_lines.append(['Errors', ', '.join(errors), ''])
            
            prefix_len = max([len(x[0]) for x in result_lines])
            amt_len = max([len(str(x[1])) for x in result_lines])
            try:
                pct_gain_len = max([len(str(abs(x[2])))for x in result_lines if isinstance(x[2], Decimal)])
            except Exception:
                # no stocks means max([]), which is an error
                # just set it to 0
                pct_gain_len = 0

            result = []
            for line in result_lines:
                if line[2]:
                    result.append('{} : {} ({} {} %)'.format(
                        line[0].ljust(prefix_len),
                        str(line[1]).rjust(amt_len),
                        '+' if line[2] >= 0 else '-',
                        str(abs(line[2])).rjust(pct_gain_len)
                    ))
                else:
                    result.append('{} : {}'.format(
                        line[0].ljust(prefix_len),
                        str(line[1]).rjust(amt_len),
                    ))
            
            result = '\n'.join(result)

            return ('{}, your balance is:\n`{}`'.format(user.display_name, result), True)
        except Exception as e:
            _logger.exception(e)
            return ('Could not report balance: {}'.format(str(e)), False)
    
    async def _handle_withdraw_command(self, command_args, message_author):
        try:
            user = self._get_user(message_author.id)
            if len(command_args) < 3:
                raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
            amount = Decimal(command_args[2])
            # make sure the user can afford the transaction
            cur_user = self._user_cache[message_author.id]
            if cur_user.balance < amount:
                raise Exception('Sorry {}, you have {}, not {}'.format(cur_user.display_name, cur_user.balance, amount))

            momocoin_amount = amount / self._exchange_rate
            momocoin_amount = Decimal(momocoin_amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

            self._db.broker_give_money_to_user(cur_user.id, -amount, 'Withdrawal to Momocoins')
            self._update_single_user(cur_user.id)
            return (self._tip_command.format(message_author.mention, momocoin_amount), True)
        except Exception as e:
            return ('No withdrawal occurred. {}'.format(str(e)), False)

    async def handle_command(self, request_id, response_id, message, bot, parser, web):
        command_args = message.content.split(' ')
        # assumption, first value in message is '$broker'
        if len(command_args) < 2:
            return ('Specify a broker operation, please', False)
        
        command = command_args[1]

        if command in self._command_mapping:
            return await self._command_mapping[command](command_args, message.author)
        else:
            return ('Did not recognize command: ' + command, False)

    async def check_for_tips(self, message):
        if message.author.id == self._tip_verifier:
            # if we have a message from the tip verifying user (mimibot)
            # then try to parse out whether they're reporting a tip. and if so, was it to ottobot?
            try:
                if message.content.startswith('Tip completed.'):
                    tip_info = message.content.split('{')[1].strip('}')
                    # this should now be 'sender_id>receiver_id:amount'
                    tip_info = tip_info.split('>')
                    sender = tip_info[0]
                    receiver = tip_info[1].split(':')[0]
                    if receiver == self._broker_id:
                        try:
                            self._get_user(sender)
                        except Exception as e:
                            return 'Ottobot thanks you for your generousity, unregistered user'
                        
                        amount = Decimal(tip_info[1].split(':')[1])
                        amount = self._exchange_rate * amount
                        amount = Decimal(amount.quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN))
                        
                        if amount != 0:
                            self._db.broker_give_money_to_user(sender, amount, 'Tipping Ottobot')
                            self._update_single_user(sender)
                            return 'Ottobot winks at you, and walks away whistling. Your pockets feel heavier. (New balance: {})'.format(self._user_cache[sender].balance)
                        else:
                            return 'That tip rounded to less than 0 cents. You get nothing, good day sir!'

            except Exception as e:
                _logger.error('Failed to process tip:({})'.format(message.content))
                _logger.exception(e)
                return 'Failed to process tip({}) Go yell at :otto:'.format(e)