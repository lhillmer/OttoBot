from dataContainers import *

import psycopg2
import psycopg2.extras

import datetime
import logging
import pickle
import copy

_logger = logging.getLogger()

class PostgresWrapper():
    def __init__(self, connectionString):
        self.connection_string = connectionString
    
    def _query_wrapper(self, query, vars=[], doFetch=True, do_log=True):
        retry = True
        connection = None
        cursor = None
        while(retry):
            try:
                connection = psycopg2.connect(self.connection_string)
                cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
                if do_log:
                    _logger.info('making Query: ' + query)
                    _logger.info('with vars: {}'.format(vars))
                cursor.execute(query, vars)
                connection.commit()
                result = None
                if(doFetch):
                    result = cursor.fetchall()
                cursor.close()
                connection.close()
                return result
            except psycopg2.InternalError as e:
                cursor.close()
                connection.close()
                if e.pgcode:
                    _logger.error("psycopg2 error code: " + str(e.pgcode))
                if not retry:
                    raise e
                retry = False

    def get_active_commands(self, do_log=True):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.commands WHERE active;", do_log=do_log)
        result = []
        for raw in rawVals:
            result.append(Command(raw))
        return result

    def get_recent_requests(self, user, when):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.requests WHERE requestedby=%s AND requested >= timestamp %s;", [user, when])
        result = []
        for raw in rawVals:
            result.append(Request(raw))
        return result

    def get_user_requests(self, user):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.requests WHERE requestedby=%s;", [user])
        result = []
        for raw in rawVals:
            result.append(Request(raw))
        return result

    def get_request(self, request_id):
        return Request(self._query_wrapper("SELECT * FROM ottobot.requests WHERE id=%s;", [request_id])[0])

    def get_ready_pending_responses(self):
        #ignore logging on this one query because it happens every 15s
        rawVals = self._query_wrapper("SELECT * FROM ottobot.pendingresponses WHERE execute <= now();", do_log=False)
        result = []
        for raw in rawVals:
            result.append(PendingResponse(raw))
        return result

    def get_responses(self, commandID, do_log=True):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.responses WHERE commandid=%s;", [commandID], do_log=do_log)
        result = []
        for raw in rawVals:
            result.append(Response(raw))
        return result

    def get_command_types(self, do_log=True):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.commandtypes;", do_log=do_log)
        result = []
        for raw in rawVals:
            result.append(CommandType(raw))
        return result

    def insert_request(self, user, commandID):
        return self._query_wrapper("INSERT INTO ottobot.requests (requestedby, requested, commandid) values (%s, %s, %s) RETURNING id;", [user, datetime.datetime.now(), commandID])[0][0]

    def insert_pending_response(self, requestID, lastResponse, when, message):
        message = copy.deepcopy(message)
        message = pickle.dumps(message)
        return self._query_wrapper("INSERT INTO ottobot.pendingresponses (requestid, nextresponse, execute, stored, message) values(%s, %s, %s, now(), %s) RETURNING id;", [requestID, lastResponse, when, message])[0][0]

    def insert_response(self, text, function, previous, commandID):
        result = self._query_wrapper("INSERT INTO ottobot.responses (text, functionname, next, previous, commandid) values (%s, %s, NULL, %s, %s) RETURNING id;", [text, function, previous, commandID])[0][0]
        self._query_wrapper("UPDATE ottobot.responses SET next=%s where commandid=%s and next IS NULL and id!=%s;", [result, commandID, result], doFetch=False)
        return result

    def insert_command(self, text, removable, caseSensitive, commandTypeID):
        return self._query_wrapper("INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid) values (%s, %s, %s, TRUE, %s) RETURNING id;", [text, removable, caseSensitive, commandTypeID])[0][0]

    def deactivate_command(self, commandID):
        self._query_wrapper("UPDATE ottobot.commands SET active=FALSE WHERE id=%s;", [commandID], doFetch=False)

    def delete_response(self, responseID, next, previous):
        self._query_wrapper("UPDATE ottobot.responses SET next=%s WHERE next=%s;", [next, responseID], doFetch=False)
        self._query_wrapper("UPDATE ottobot.responses SET previous=%s WHERE previous=%s;", [previous, responseID], doFetch=False)
        self._query_wrapper("DELETE FROM ottobot.responses WHERE id=%s;", [responseID], doFetch=False)

    def delete_pending_response(self, pendingResponseID):
        self._query_wrapper("DELETE FROM ottobot.pendingresponses WHERE id=%s;", [pendingResponseID], doFetch=False)

    def broker_create_user(self, user_id, display_name):
        return self._query_wrapper("SELECT ottobroker.createuser(%s, %s);", [user_id, display_name])
    
    def broker_get_single_user(self, user_id):
        return BrokerUser(self._query_wrapper("SELECT * FROM ottobroker.users WHERE id=%s;", [user_id])[0])
    
    def broker_get_all_users(self):
        rawVals = self._query_wrapper("SELECT * FROM ottobroker.users;", [])
        result = []
        for raw in rawVals:
            result.append(BrokerUser(raw))
        return result
    
    def broker_get_stocks_by_user(self, user_id):
        rawVals = self._query_wrapper("SELECT * FROM ottobroker.fakestocks WHERE userid=%s and sold is NULL;", [user_id])
        result = []
        for raw in rawVals:
            result.append(BrokerStock(raw))
        return result
    
    def broker_give_money_to_user(self, user_id, amount, reason):
        return self._query_wrapper("SELECT ottobroker.givemoney(%s, %s, %s);", [user_id, amount, reason])
    
    def broker_buy_regular_stock(self, user_id, ticker_symbol, ticker_value, quantity):
        return self._query_wrapper("SELECT ottobroker.buyregularstock(%s, %s, %s, %s);", [user_id, ticker_symbol, ticker_value, quantity])
    
    def broker_sell_stock(self, user_id, ticker_symbol, ticker_value, quantity):
        return self._query_wrapper("SELECT ottobroker.sellstock(%s, %s, %s, %s);", [user_id, ticker_symbol, ticker_value, quantity])