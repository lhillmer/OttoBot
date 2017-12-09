from webWrapper import RestWrapper

import json
import logging

_logger = logging.getLogger()

class CryptoConverter():
    def __init__(self, webWrapper):
        self.rest = ResstWrapper(webWrapper,
            "https://min-api.cryptocompare.com/data", {})

    async def get_symbols(self):
        result = []

        data = json.loads(await self.rest.request("/all/coinlist", {}))
        if data['Response'] == 'Success':
            for i in data['Data']:
                result.append(i)
        else:
            _logger.error("Issue with crypto request: " + data['Response']
        return result

    async def convert(self, base_type, target_types):
        result = {}

        data = json.loads(await self.rest.request("/price", {'fsym': base_type.upper(), 'tsyms':target_types.join(',').upper()}))
        for i in data:
            if i not in target_types:
                _logger.error("unexpected value in conversion response: " + i)
            else:
                result[i] = data[i]
        return result