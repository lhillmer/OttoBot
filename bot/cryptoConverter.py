from webWrapper import RestWrapper
from stockInfo import StockInfo

import json
import logging

_logger = logging.getLogger()

class CryptoConverter():
    def __init__(self, webWrapper, api_key):
        self.rest = RestWrapper(webWrapper, "https://pro-api.coinmarketcap.com", {'CMC_PRO_API_KEY': api_key})

    async def get_info(self, crypto_symbol):
        crypto_symbol = crypto_symbol.upper()
        response = await self.rest.request("/v1/cryptocurrency/quotes/latest", {'symbol': crypto_symbol})
        parsed_response = json.loads(await response.text())
        try:
            main_data = parsed_response['data'][crypto_symbol]
            result = {
                "Price": StockInfo.decimalize_string(str(main_data['quote']['USD']['price']), post_decimal_digits=4),
                "24h % Change": main_data['quote']['USD']['percent_change_24h'],
                "Marketcap": StockInfo.get_wordy_num(main_data['quote']['USD']['market_cap']),
            }
        except Exception as e:
            result = str(e)
            _logger.error("Error occurred parsing crypto data: " + result)
            _logger.exception(e)
        return result
    