import psycopg2
import datetime
#TODO:have inserts return ids of created objects

class PostgresWrapper():
    def __init__(self):
        self.connection_string = "host='localhost' dbname='postgres' user='postgres' password='postgres'"
        self.connection = psycopg2.connect(self.connection_string)
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.DictCursor)

    def get_active_commands(self):
        self.cursor.execute("SELECT * FROM ottobot.commands WHERE active")
        return self.cursor.fetchall()

    def get_recent_requests(self, user, when):
        self.cursor.execute("SELECT * FROM ottobot.requests WHERE requestedby=%s AND requested >= timestamp %s", user, when)
        return self.cursor.fetchall()

    def get_user_requests(self, user, when):
        self.cursor.execute("SELECT * FROM ottobot.requests WHERE requestedby=%s", user)
        return self.cursor.fetchall()

    def get_pending_responses(self):
        self.cursor.execute("SELECT * FROM ottobot.pending_responses")
        return self.cursor.fetchall()

    def get_responses(self, commandID):
        self.cursor.execute("SELECT * FROM ottobot.responses WHERE commandid=%s", commandID)
        return self.cursor.fetchall()

    def get_command_types(self):
        self.cursor.execute("SELECT * FROM ottobot.commandtypes")
        return self.cursor.fetchall()

    def insert_request(self, user, commandID):
        self.cursor.execute("INSERT INTO ottobot.requests (requested, requestedby, commandid) values (%s, %s, %s) RETURNING id;", user, datetime.datetime.now(), commandID)
        return self.cursor.fetchall()

    def insert_pending_response(self, requestID, lastResponse, when):
        self.cursor.execute("INSERT INTO ottobot.pendingresponses (requestid, previousresponse, execute, stored) values(%s, %s, %s, %s) RETURNING id;", requestID, lastResponse, when, datetime.datetime.now())
        return self.cursor.fetchall()

    def insert_response(self, text, function, after, commandID):
        self.cursor.execute("INSERT INTO ottobot.responses (text, functionname, after, commandid) values (%s, %s, %s, %s) RETURNING id;", text, function, after, commandID)
        return self.cursor.fetchall()

    def insert_command(self, text, removable, caseSensitive, commandTypeID):
        self.cursor.execute("INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid) values (%s, %s, %s, TRUE, %s) RETURNING id;", text, removable, caseSensitive, commandTypeID)
        return self.cursor.fetchall()

    def deactivate_command(self, commandID):
        self.cursor.execute("UPDATE ottobot.commands SET active=FALSE WHERE id=%s", commandID)

    def delete_response(self, responseID, after):
        self.cursor.execute("UPDATE ottobot.responses SET after=%s WHERE after=%s", after, responseID)
        self.cursor.execute("DELETE FROM ottobot.responses WHERE id=%s")

    def delete_pending_response(self, pendingResponseID):
        self.cursor.execute("DELETE FROM ottobot.pendingresponses WHERE id=%s", pendingResponseID)
