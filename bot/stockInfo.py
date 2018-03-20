from webWrapper import RestWrapper

import json
import logging
import datetime

_logger = logging.getLogger()

class StockInfo():
    def __init__(self, webWrapper, api_key):
        self.rest = RestWrapper(webWrapper,
            "https://www.alphavantage.co/query", {'apikey': api_key})
        self.day_format = '%Y-%m-%d'
        self.error_message_key = 'Error Message'

    async def daily_values(self, symbol):
        result = {}
        response = await self.rest.request('', {'function':'TIME_SERIES_DAILY', 'symbol': symbol})
        data = json.loads(await response.text())
        if self.error_message_key in data:
            _logger.error('Error with api call: ' + data[self.error_message_key])
            raise Exception('API call failed. Check your symbol?')
        try:
            days = data['Time Series (Daily)']
        except KeyError as e:
            raise KeyError(e, 'Well, I certainly wasn\'t excpecting that structure')
        # only grab today's data
        today = datetime.datetime.now().strftime(self.day_format)
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(self.day_format)
        if today in days:
            result = days[today]
            result['6. day'] = today
        elif yesterday in days:
            result = days[yesterday]
            result['6. day'] = yesterday
        else:
            raise Exception("Couldn't find today's data(%s) or yesterdays data(%s)??" % (today, yesterday))
        return result
