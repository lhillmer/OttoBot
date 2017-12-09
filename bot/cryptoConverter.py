from webWrapper import RestWrapper

import json
import logging

_logger = logging.getLogger()

class CryptoConverter():
    def __init__(self, webWrapper):
        self.rest = RestWrapper(webWrapper,
            "https://min-api.cryptocompare.com/data", {})

    async def get_symbols(self):
        result = []
        response = await self.rest.request('/all/coinlist', {})
        data = json.loads(await response.text())
        if data['Response'] == 'Success':
            for i in data['Data']:
                result.append(i)
        else:
            _logger.error("Issue with crypto request: " + data['Response'])
        return result

    async def convert(self, base_type, target_types):
        result = {}
        response = await self.rest.request("/price", {'fsym': base_type, 'tsyms':','.join(target_types)})
        data = json.loads(await response.text())
        for i in data:
            if i not in target_types:
                _logger.error("unexpected value in conversion response: " + i)
            else:
                result[i] = data[i]
        return result
