import pickle

class CommandType():
    def __init__(self,raw):
        self.id = raw[0]
        self.name = raw[1]


class Response():
    def __init__(self, raw):
        self.id = raw[0]
        self.text = raw[1]
        self.function = raw[2]
        self.next = raw[3]
        self.previous = raw[4]
        self.command_id = raw[5]


class PendingResponse():
    def __init__(self, raw):
        self.id = raw[0]
        self.request_id = raw[1]
        self.next_response = raw[2]
        self.stored = raw[3]
        self.execute = raw[4]
        self.message = pickle.loads(raw[5])


class Request():
    def __init__(self, raw):
        self.id = raw[0]
        self.command_id = raw[1]
        self.requested = raw[2]
        self.requested_by = raw[3]


class Command():
    def __init__(self, raw):
        self.id = raw[0]
        self.text = raw[1]
        self.removable = raw[2]
        self.case_sensitive = raw[3]
        self.active = raw[4]
        self.command_type_id = raw[5]

    def is_equivalent_matcher(self, other):
        if not isinstance(other, Command):
            return False
        if other.case_sensitive and self.case_sensitive:
            return other.command_type_id == self.command_type_id and other.text == self.text
        elif not other.case_sensitive and not self.case_sensitive:
            return other.command_type_id == self.command_type_id and other.text.upper() == self.text.upper()

class BrokerUser():
    def __init__(self, raw):
        self.id = raw[0]
        self.display_name = raw[1]
        self.balance = raw[2]

class BrokerStock():
    def __init__(self, raw):
        self.id = raw[0]
        self.stock_type = raw[1]
        self.user_id = raw[2]
        self.transaction_id = raw[3]
        self.ticker_symbol = raw[4]
        self.purchase_cost = raw[5]
        self.purchase_time = raw[6]
        self.expiration_time = raw[7]
        self.sell_cost = raw[8]
        self.sell_time = raw[9]