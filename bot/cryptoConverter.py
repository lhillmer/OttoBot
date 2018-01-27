from webWrapper import RestWrapper

import json
import logging

_logger = logging.getLogger()

class CryptoConverter():
    def __init__(self, webWrapper):
        self.rest = RestWrapper(webWrapper,
            "https://api.coinmarketcap.com", {})

    async def get_symbols(self):
        result = {}
        response = await self.rest.request('/v1/ticker', {})
        data = json.loads(await response.text())
        if data:
            for coin in data:
                result[coin['symbol']] = coin['id']
        else:
            _logger.error("Issue with crypto request")
        return result

    async def convert(self, base_type, target_type):
        result = 0
        response = await self.rest.request("/v1/ticker/" + base_type, {'convert': target_type.upper()})
        data = json.loads(await response.text())
        try:
            result = float(data[0]['price_' + target_type.lower()])
        except Exception as e:
            _logger.error("something happened in conversion: " + str(e))
        return result
    
    async def market_cap(self, coin=None):
        result = 0
        
        if coin is None:
            response = await self.rest.request("/v1/global", {})
            data = json.loads(await response.text())
            try:
                result = data['total_market_cap_usd']
            except Exception as e:
                _logger.error("Exception trying to get total market cap: " + str(e))
        else:
            response = await self.rest.request("/v1/ticker/" + coin, {})
            data = json.loads(await response.text())
            try:
                result = float(data[0]['market_cap_usd'])
            except Exception as e:
                _logger.error("Exception trying to get coin %s market cap: %s" % (str(coin), str(e)))
            
        return result
