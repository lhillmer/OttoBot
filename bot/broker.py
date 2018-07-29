from webWrapper import RestWrapper, SynchronousRestWrapper

import json
import logging
import datetime
import pytz
import copy
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

_logger = logging.getLogger()

class OttoBroker():
    STATUS_KEY = 'status'
    MESSAGE_KEY = 'message'

    STATUS_SUCCESS = 'success'

    def __init__(self, webWrapper, db, broker_id, super_user_role, tip_verifier, exchange_rate, tip_command, broker_api_key):
        self._stock_api = RestWrapper(webWrapper, "https://api.iextrading.com/1.0", {})

        self._broker_api = SynchronousRestWrapper("http://otto.runtimeexception.net/broker", {})
        self._broker_api_key = broker_api_key
        
        self._tip_verifier = tip_verifier
        self._exchange_rate = Decimal(exchange_rate)
        self._broker_id = broker_id
        self._tip_command = tip_command
        self._super_user_role = super_user_role

        self._command_mapping = {
            'register': self._handle_register,
            'balance': self._handle_balance,
            'buystock': self._handle_buy_long,
            'sellstock': self._handle_sell_long,
            'buyshort': self._handle_buy_short,
            'sellshort': self._handle_sell_short,
            'withdraw': self._handle_withdraw_command,
            'testmode': self._handle_test_mode,
            'watch': self._handle_watch,
            'unwatch': self._handle_unwatch,
            'help': self._handle_help
        }

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
            response = await self._stock_api.request('/stock/market/batch/', {'types': 'quote', 'symbols': ','.join(symbol_list)})
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
                        known_symbols[symbol] = Decimal(str(data[symbol]['quote']['latestPrice']))
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
    
    def _broker_api_wrapper(self, endpoint, params):
        unparsed = self._broker_api.request(endpoint, params)
        data = None
        try:
            data = json.loads(unparsed)
        except Exception:
            raise Exception('Invalid Broker API response: {}'.format(unparsed))
        if not isinstance(data, dict):
            raise Exception('From broker, unexpected data type ' + str(type(data)))
        
        if data[self.STATUS_KEY] == self.STATUS_SUCCESS:
            return data
        else:
            raise Exception('Broker API trying to access endpoint {}, returned error {}'.format(endpoint, data['message']))
    
    def _get_test_mode(self):
        return self._broker_api_wrapper('/test_mode', {})['test_mode']
        
    def _get_user(self, user_id):
        return self._broker_api_wrapper('/user_info',{'userid': user_id, 'shallow': 'false', 'historical': 'true'})['user']
    
    async def _handle_buy_long(self, command_args, message_author):
        user = self._get_user(message_author.id)
        if len(command_args) < 4:
            raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
        symbol = command_args[2]
        quantity = self._get_int(command_args[3])
        
        data = self._broker_api_wrapper('/buy_long',
            {
                'userid': user['id'],
                'apikey': self._broker_api_key,
                'symbol': symbol,
                'quantity': quantity
            }
        )

        user = data['user']
        
        return (
            '{}, You purchased {} {} at {} each, for a total cost of {}'.format(
                user['display_name'],
                data['quantity'],
                data['symbol'],
                data['per_stock_amt'],
                data['total_amt']),
            True
        )

    async def _handle_sell_long(self, command_args, message_author):
        user = self._get_user(message_author.id)
        if len(command_args) < 4:
            raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
        symbol = command_args[2]
        quantity = self._get_int(command_args[3])
        
        data = self._broker_api_wrapper('/sell_long',
            {
                'userid': user['id'],
                'apikey': self._broker_api_key,
                'symbol': symbol,
                'quantity': quantity
            }
        )

        user = data['user']
        
        return (
            '{}, You sold {} {} at {} each, for a total gain of {}.\nYou now have {}'.format(
                user['display_name'],
                data['quantity'],
                data['symbol'],
                data['per_stock_amt'],
                data['total_amt'],
                user['balance']),
            True
        )
    
    async def _handle_buy_short(self, command_args, message_author):
        user = self._get_user(message_author.id)
        if len(command_args) < 4:
            raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
        symbol = command_args[2]
        quantity = self._get_int(command_args[3])
        
        data = self._broker_api_wrapper('/buy_short',
            {
                'userid': user['id'],
                'apikey': self._broker_api_key,
                'symbol': symbol,
                'quantity': quantity
            }
        )

        user = data['user']
        
        return (
            '{}, You purchased {} {} at {} each, for a total cost of {}'.format(
                user['display_name'],
                data['quantity'],
                data['symbol'],
                data['per_stock_amt'],
                data['total_amt']),
            True
        )

    async def _handle_sell_short(self, command_args, message_author):
        user = self._get_user(message_author.id)
        if len(command_args) < 4:
            raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
        symbol = command_args[2]
        quantity = self._get_int(command_args[3])
        
        data = self._broker_api_wrapper('/sell_short',
            {
                'userid': user['id'],
                'apikey': self._broker_api_key,
                'symbol': symbol,
                'quantity': quantity
            }
        )

        user = data['user']
        
        return (
            '{}, You sold {} {} at {} each, for a total gain of {}.\nYou now have {}'.format(
                user['display_name'],
                data['quantity'],
                data['symbol'],
                data['per_stock_amt'],
                data['total_amt'],
                user['balance']),
            True
        )
    
    async def _handle_register(self, command_args, message_author):
        user = self._broker_api_wrapper('/register',
            {
                'userid': message_author.id,
                'displayname': message_author.name,
                'apikey': self._broker_api_key
            }
        )['user']

        return ('Welcome, {}. You have a starting balance of {}'.format(user['display_name'], user['balance']), True)
    
    @staticmethod
    def _format_section_helper(lines):
        result = []
        prefix_len = max([len(x[0]) for x in lines])
        amt_len = max([len(str(x[1])) for x in lines])
        try:
            pct_gain_len = max([len(str(abs(x[2])))for x in lines if isinstance(x[2], Decimal)])
        except Exception:
            # no stocks means max([]), which is an error
            # just set it to 0
            pct_gain_len = 0

        for line in lines:
            if line[2] is not None:
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
        
        return result

    async def _handle_balance(self, command_args, message_author):
        try:
            user = self._get_user(message_author.id)

            errors = []

            cash = user['balance']
            assets_total = Decimal(user['assets'])
            assets_orig_total = Decimal(cash)
            asset_lines = [
                ['Cash', cash, None]
            ]

            liabilities_total = Decimal(user['liabilities'])
            liabilities_orig_total = Decimal(0)
            liability_lines = []

            for stock in user['longs']:
                count = sum([x['count'] for x in user['longs'][stock]['stocks']])
                cur_purchase_stock = sum([Decimal(x['purchase_cost']) * x['count'] for x in user['longs'][stock]['stocks']])
                full_stock_value = Decimal(user['longs'][stock]['total_value'])
                assets_orig_total += cur_purchase_stock

                asset_lines.append([
                    '{} {}'.format(count, stock),
                    full_stock_value,
                    (Decimal(100) * (full_stock_value - cur_purchase_stock) / cur_purchase_stock).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                ])

            if assets_orig_total == 0:
                asset_lines.append([
                    'Total',
                    assets_total,
                    Decimal(0)
                ])
            else:
                asset_lines.append([
                    'Total',
                    assets_total,
                    (Decimal(100) * (assets_total - assets_orig_total) / assets_orig_total).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                ])

            for stock in user['shorts']:
                count = sum([x['count'] for x in user['shorts'][stock]['stocks']])
                cur_sold_stock = sum([Decimal(x['sell_cost']) * x['count'] for x in user['shorts'][stock]['stocks']])
                full_stock_value = Decimal(user['shorts'][stock]['total_value'])
                liabilities_orig_total += cur_sold_stock

                liability_lines.append([
                    '{} {}'.format(count, stock),
                    full_stock_value,
                    (Decimal(100) * (1 - (full_stock_value / cur_sold_stock))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                ])

            if liabilities_orig_total == 0:
                liability_lines.append([
                    'Total',
                    liabilities_total,
                    Decimal(0)
                ])
            else:
                liability_lines.append([
                    'Total',
                    liabilities_total,
                    (Decimal(100) *  (1 - (liabilities_total / liabilities_orig_total))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                ])

            result = [
                'Assets:'
            ]
            result.extend(self._format_section_helper(asset_lines))
            result.append('')
            result.append('Liabilities:')
            result.extend(self._format_section_helper(liability_lines))
            result.append('')
            result.append('Net Worth: {}'.format(assets_total - liabilities_total))

            if errors:
                result.append('Errors: {}'.format(', '.join(errors)))
            
            result = '\n'.join(result)

            return ('{}, your balance is:\n`{}`'.format(user['display_name'], result), True)
        except Exception as e:
            _logger.exception(e)
            return ('Could not report balance: {}'.format(str(e)), False)
    
    async def _handle_withdraw_command(self, command_args, message_author):
        if len(command_args) < 3:
            raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
        
        if self._get_test_mode():
            raise Exception('No withdrawing in test mode')

        user = self._get_user(message_author.id)
        amount = command_args[2]
        data = self._broker_api_wrapper('/withdraw',
            {
                'userid': user['id'],
                'apikey': self._broker_api_key,
                'amount': amount,
                'reason': 'Withdrawal to Momocoins'
            }
        )

        user = data['user']

        # pull the amount from the response, just in case
        amount = Decimal(data['amount'])
        momocoin_amount = amount / self._exchange_rate
        momocoin_amount = Decimal(momocoin_amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
        return (self._tip_command.format(message_author.mention, momocoin_amount), True)

    async def _handle_test_mode(self, command_args, message_author):
        is_super_user = False
        for role in message_author.roles:
            if role.name == self._super_user_role:
                is_super_user = True
                break

        if is_super_user:
            active = self._broker_api_wrapper('/toggle_test_mode', {'apikey': self._broker_api_key})['test_mode']
            return ('Test mode is ' + ('enabled' if active else 'disabled'), True)
        else:
            return ('Can\'t let you do that, StarFox. Test mode is still ' + ('enabled' if self._get_test_mode() else 'disabled'), False)

    async def _handle_watch(self, command_args, message_author):
        if len(command_args) < 3:
            raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
        
        user = self._get_user(message_author.id)
        symbol = command_args[2]
        data = self._broker_api_wrapper('/set_watch',
            {
                'userid': user['id'],
                'apikey': self._broker_api_key,
                'symbol': symbol,
            }
        )

        user = data['user']
        return ('{} has been added to your watches, {}'.format(symbol.upper(), user['display_name']), True)

    async def _handle_unwatch(self, command_args, message_author):
        if len(command_args) < 3:
            raise Exception('Sorry, you don\'t seem to have enough values in your message for me to parse.')
        
        user = self._get_user(message_author.id)
        symbol = command_args[2]
        data = self._broker_api_wrapper('/remove_watch',
            {
                'userid': user['id'],
                'apikey': self._broker_api_key,
                'symbol': symbol,
            }
        )

        user = data['user']
        return ('{} has been removed from your watches, {}'.format(symbol.upper(), user['display_name']), True)
        
    async def _handle_help(self, command_args, message_author):
        result = 'Supported commands:\n'
        cmd_lines = []
        for cmd in self._command_mapping:
            cmd_lines.append('`$broker {}`'.format(cmd))

        return (result + '\n'.join(cmd_lines), True)

    async def handle_command(self, request_id, response_id, message, bot, parser, web):
        command_args = message.content.split(' ')
        # assumption, first value in message is '$broker'
        if len(command_args) < 2:
            return ('Specify a broker operation, please', False)
        
        command = command_args[1]

        if command in self._command_mapping:
            try:
                return await self._command_mapping[command](command_args, message.author)
            except Exception as e:
                return ('Operation failed: {}'.format(e), False)
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
                            user = self._get_user(sender)
                        except Exception as e:
                            return 'Ottobot thanks you for your generousity, unregistered user'
                        
                        amount = Decimal(tip_info[1].split(':')[1])
                        amount = self._exchange_rate * amount
                        amount = Decimal(amount.quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN))
                        
                        # just an arbitrary way to force money into the test account. 
                        if self._get_test_mode():
                            amount = 15000
                        
                        if amount > 0:
                            data = self._broker_api_wrapper('/deposit',
                                {
                                    'userid': sender,
                                    'apikey': self._broker_api_key,
                                    'amount': amount,
                                    'reason': 'Withdrawal to Momocoins'
                                }
                            )

                            user = data['user']
                            return 'Ottobot winks at you, {}, and walks away whistling. Your pockets feel heavier. (New balance: {})'.format(
                                user['display_name'],
                                user['balance']
                            )
                        else:
                            return 'That tip rounded to 0 cents. You get nothing, good day sir!'

            except Exception as e:
                _logger.error('Failed to process tip:({})'.format(message.content))
                _logger.exception(e)
                return 'Failed to process tip({}) Go yell at :otto:'.format(e)