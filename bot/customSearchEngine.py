from webWrapper import RestWrapper

import json
import logging

_logger = logging.getLogger()


class SearchResponse():
    def __init__(self, status, items, errorMessage=None):
        self.status = status
        self.items = items
        self.error_message = errorMessage


class ResponseSummary():
    def __init__(self, title, link):
        self.title = title
        self.link = link


class CustomSearchEngine():
    def __init__(self, webWrapper, cx, apiKey):
        self.rest = RestWrapper(webWrapper, 
                "https://www.googleapis.com/customsearch/v1",
                {'cx': cx, 'key': apiKey})

    async def search(self, query):
        response = await self.rest.request("", {'q': query, 'num': '1'})
        result = SearchResponse(response.status, [])

        if response.status == 200:
            data = json.loads(await response.text())
            if int(data['searchInformation']['totalResults']) > 0:
                for i in data['items']:
                    result.items.append(ResponseSummary(i['title'], i['link']))
        else:
            errors = json.loads(await response.text())
            _logger.error("Issue with cse request: " + errors['error']['message'])
            result.error_message = errors['error']['message']
            

        return result
