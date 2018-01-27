from dataContainers import CommandType
from dataContainers import Response
from dataContainers import PendingResponse
from dataContainers import Request
from dataContainers import Command

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
        self.connection = psycopg2.connect(self.connection_string)
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    def _query_wrapper(self, query, vars=[], doFetch=True, doLog=True):
        retry = True
        while(retry):
            try:
                if doLog:
                    _logger.info('making Query: ' + query)
                for v in vars:
                    _logger.info('val: %s', str(v))
                self.cursor.execute(query, vars)
                self.connection.commit()
                if(doFetch):
                    return self.cursor.fetchall()
                return
            except psycopg2.InternalError as e:
                if e.pgcode:
                    _logger.error("psycopg2 error code: " + str(e.pgcode))
                retry = False

    def get_active_commands(self, do_log=True):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.commands WHERE active;", do_log)
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
        rawVals = self._query_wrapper("SELECT * FROM ottobot.pendingresponses WHERE execute <= now();", doLog=False)
        result = []
        for raw in rawVals:
            result.append(PendingResponse(raw))
        return result

    def get_responses(self, commandID, do_log=True):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.responses WHERE commandid=%s;", [commandID], do_log)
        result = []
        for raw in rawVals:
            result.append(Response(raw))
        return result

    def get_command_types(self, do_log=True):
        rawVals = self._query_wrapper("SELECT * FROM ottobot.commandtypes;", do_log)
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
