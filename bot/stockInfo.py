from webWrapper import RestWrapper

import json
import logging
import datetime
import pytz
import copy

_logger = logging.getLogger()

class StockInfo():
    def __init__(self, webWrapper, iex_api_key):
        self.rest = RestWrapper(webWrapper,
            "https://cloud.iexapis.com/stable", {'token': iex_api_key})
        self.date_time_format = '%Y-%m-%d %H:%M:%S'
        self.date_format = '%Y-%m-%d'
        self.error_key = 'Error'
        self.open_key = 'Open'
        self.open_dt_key = 'Open (Time)'
        self.close_key = 'Close'
        self.close_dt_key = 'Close (Time)'
        self.live_key = 'Live'
        self.live_dt_key = 'Live (Time)'
        self.average_key = 'Average'
        self.debug_dt_key = 'OttoTime'
        self.high_key = 'High'
        self.low_key = 'Low'
        self.date_key = 'Date'
        self.duration_key = 'Duration'
        self.endpoint_key = 'Endpoint'
        self.market_cap_key = 'MarketCap'
        self.latest_source_key = 'LatestSource'
        self.base_market_cap_key = 'BaseMarketCap'
        self.company_name_key = 'CompanyName'
        self.pe_ratio_key = 'PE Ratio'
        self.change_percent_key = 'Change %'
        self.latest_volume_key = 'LatestVolume'
        self.average_volume_key = 'AverageVolume'

    @staticmethod
    def is_market_live(time=None):
        if time is None:
            time = datetime.datetime.now(pytz.timezone('EST5EDT'))
        return (time.hour > 9 or (time.hour == 9 and time.minute >= 30)) and time.hour < 16
    
    @staticmethod
    def get_wordy_num(num):
        result = str(num)
        words = ["", "Thousand", "Million", "Billion", "Trillion "]

        for word in words:
            if num > 1000:
                num = num / 1000
            else:
                break


        return ("{0:.2f}".format(num) + " " + word).strip()
    
    @staticmethod
    def duration_call(duration):
        # define a month to be the shortest month because that's easiest
        # then, figure out the shortest appropriate chart call
        durations = [
            (28, '1m'),
            (8, '3m'),
            (168, '6m'),
            (364, '1y'),
            (729, '2y'),
            (1823, '5y')
            ]
        
        # need to have a duration of at least 1 day
        duration = max(duration, 1)
        
        for i in range(len(durations)):
            if duration <= durations[i][0]:
                return duration, durations[i][1]

        return durations[-1][0], durations[-1][1]
    
    async def moving_average(self, symbol, duration=-1, debug=False):
        if duration == -1:
            duration = 30
        symbol = symbol.upper()
        duration, duration_endpoint = self.duration_call(duration)
        try:
            response = await self.rest.request('/stock/%s/chart/%s' % (symbol, duration_endpoint) , {})
            unparsed = await response.text()
            data = None
            try:
                data = json.loads(unparsed)
            except Exception:
                pass
            if data is None:
                result = {
                    self.error_key: unparsed
                }
            elif not isinstance(data, list):
                result = {
                    self.error_key: 'Unexpected data type ' + str(type(data))
                }
            else:

                single_day = data[-1]
                to_average = [single_day['close']]
                days = [single_day['date']]

                for i in range(-2, -(duration + 1), -1):
                    single_day = data[i]
                    to_average.append(single_day['close'])
                    days.append(single_day['date'])
                
                result = {
                    self.average_key: (sum(to_average) / len(to_average))
                }
                    
                if debug:
                    result[self.debug_dt_key] = datetime.datetime.now().strftime(self.date_time_format)
                    result[self.date_key] = days
                    result[self.duration_key] = duration
                    result[self.endpoint_key] = duration_endpoint
        except Exception as e:
            result = {
                self.error_key: str(e)
            }
        return result
    
    async def duration(self, symbol, duration=-1, debug=False):
        if duration == -1:
            duration = 5
        symbol = symbol.upper()
        duration, duration_endpoint = self.duration_call(duration)
        try:
            response = await self.rest.request('/stock/%s/chart/%s' % (symbol, duration_endpoint) , {})
            unparsed = await response.text()
            data = None
            try:
                data = json.loads(unparsed)
            except Exception:
                pass
            if data is None:
                result = {
                    self.error_key: unparsed
                }
            elif not isinstance(data, list):
                result = {
                    self.error_key: 'Unexpected data type ' + str(type(data))
                }
            else:

                single_day = data[-1]
                _logger.warn('starting with day: ' + str(-1))
                result = {
                    self.open_key: single_day['open'],
                    self.high_key: single_day['high'],
                    self.low_key: single_day['low'],
                    self.close_key: single_day['close']
                }
                close_date = single_day['date']
                open_date = single_day['date']
                days = [single_day['date']]
                
                for i in range(-2, -(duration + 1), -1):
                    _logger.warn('finding day: ' + str(i))
                    single_day = data[i]
                    result[self.open_key] = single_day['open']
                    open_date = single_day['date']
                    if single_day['high'] > result[self.high_key]:
                        result[self.high_key] = single_day['high']
                    if single_day['low'] < result[self.low_key]:
                        result[self.low_key] = single_day['low']
                    days.append(single_day['date'])
                
                if debug:
                    result[self.debug_dt_key] = datetime.datetime.now().strftime(self.date_time_format)
                    result[self.open_dt_key] = open_date
                    result[self.close_dt_key] = close_date
                    result[self.date_key] = days
                    result[self.duration_key] = duration
                    result[self.endpoint_key] = duration_endpoint
        except Exception as e:
            result = {
                self.error_key: str(e)
            }

        return result
    
    async def daily(self, symbol, debug=False):
        if not self.is_market_live():
            return await self.live(symbol, debug=debug)
        
        symbol = symbol.upper()
        try:
            response = await self.rest.request('/stock/%s/chart' % symbol , {})
            unparsed = await response.text()
            data = None
            try:
                data = json.loads(unparsed)
            except Exception:
                pass
            if data is None:
                result = {
                    self.error_key: unparsed
                }
            elif not isinstance(data, list):
                result = {
                    self.error_key: 'Unexpected data type ' + str(type(data))
                }
            else:
                # assumes data is sorted oldest first
                yesterday = data[-1]
                result = {
                    self.open_key: yesterday['open'],
                    self.high_key: yesterday['high'],
                    self.low_key: yesterday['low'],
                    self.close_key: yesterday['close']
                }
                if debug:
                    result[self.debug_dt_key] = datetime.datetime.now().strftime(self.date_time_format)
                    result[self.date_key] = yesterday['date']
        except Exception as e:
            result = {
                self.error_key: str(e)
            }

        return result


    async def live(self, symbol, debug=False):
        symbol = symbol.upper()
        try:
            response = await self.rest.request('/stock/%s/quote' % symbol , {})
            unparsed = await response.text()
            data = None
            try:
                data = json.loads(unparsed)
            except Exception:
                pass
            if data is None:
                result = {
                    self.error_key: unparsed
                }
            elif not isinstance(data, dict):
                result = {
                    self.error_key: 'Unexpected data type ' + str(type(data))
                }
            else:
                market_cap = 'ERROR'
                try:
                    market_cap = self.get_wordy_num(int(data.get('marketCap', '0')))
                except:
                    pass
                
                change_percent = 'ERROR'
                try:
                    change_percent = str(float(data.get('changePercent', '0')) * 100)
                    if '.' in change_percent:
                        dot_pos = index('.')
                        _logger.info("index of . in {} is {}".format(dot_pos, change_percent))
                        change_percent = change_percent[0:dot_pos + 3]
                    else:
                        change_percent = "bwuh"
                except:
                    pass

                result = {
                    self.company_name_key: data.get('companyName', 'ERROR'),
                    self.open_key: data.get('open', 'ERROR'),
                    self.market_cap_key: market_cap,
                    self.high_key: data.get('high', 'ERROR'),
                    self.low_key: data.get('low', 'ERROR'),
                    self.change_percent_key: change_percent,
                    self.pe_ratio_key: data.get('peRatio', 'ERROR'),
                    self.latest_volume_key: self.get_wordy_num(data.get('latestVolume', 'ERROR')),
                    self.average_volume_key: self.get_wordy_num(data.get('avgTotalVolume', 'ERROR')),
                }
                using_close = False
                if data['latestSource'] == 'Close':
                    result[self.close_key] = data['close']
                    using_close = True
                else:
                    result[self.live_key] = data['latestPrice']
                if debug:
                    result[self.latest_source_key] = data['latestSource']
                    result[self.base_market_cap_key] = data['marketCap']
                    result[self.debug_dt_key] = datetime.datetime.now().strftime(self.date_time_format)
                    result[self.open_dt_key] = datetime.datetime.fromtimestamp(data['openTime']/1000.0).astimezone(pytz.timezone('EST5EDT')).strftime(self.date_time_format)
                    if using_close:
                        result[self.close_dt_key] = datetime.datetime.fromtimestamp(data['closeTime']/1000.0).astimezone(pytz.timezone('EST5EDT')).strftime(self.date_time_format)
                    else:
                        result[self.live_dt_key] = datetime.datetime.fromtimestamp(data['latestUpdate']/1000.0).astimezone(pytz.timezone('EST5EDT')).strftime(self.date_time_format)
        except Exception as e:
            result = {
                self.error_key: str(e)
            }

        return result
