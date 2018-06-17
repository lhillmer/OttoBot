CREATE SCHEMA IF NOT EXISTS ottobot;
CREATE TABLE ottobot.commandtypes(
    id serial NOT NULL,
    name varchar(256) NOT NULL,
    PRIMARY KEY(id)
);
CREATE TABLE ottobot.commands(
    id serial NOT NULL,
    text varchar(256) NOT NULL,
    removable boolean NOT NULL,
    casesensitive boolean NOT NULL,
    active boolean NOT NULL,
    commandtypeid int NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(commandtypeid) REFERENCES ottobot.commandtypes(id)
);
CREATE TABLE ottobot.responses(
    id serial NOT NULL,
    text varchar(256),
    functionname varchar(256),
    next int,
    previous int,
    commandid int NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(commandid) REFERENCES ottobot.commands(id),
    FOREIGN KEY(next) REFERENCES ottobot.responses(id),
    FOREIGN KEY(previous) REFERENCES ottobot.responses(id)
);
CREATE TABLE ottobot.requests(
    id serial NOT NULL,
    commandid int NOT NULL,
    requested timestamp,
    requestedby varchar(256),
    PRIMARY KEY(id),
    FOREIGN KEY(commandid) REFERENCES ottobot.commands(id)
);
CREATE TABLE ottobot.pendingresponses(
    id serial NOT NULL,
    requestid int NOT NULL,
    nextresponse int NOT NULL,
    stored timestamp,
    execute timestamp NOT NULL,
    message bytea,
    PRIMARY KEY(id),
    FOREIGN KEY(requestid) REFERENCES ottobot.requests(id),
    FOREIGN KEY(nextresponse) REFERENCES ottobot.responses(id)
);
INSERT INTO ottobot.commandtypes (name) values ('STARTS_WITH'), ('CONTAINS'), ('EQUALS');

CREATE SCHEMA IF NOT EXISTS ottobroker;
    CREATE TABLE ottobroker.users(
        id varchar(256) NOT NULL,
        created TIMESTAMP NOT NULL,
        displayname varchar(256) NOT NULL,
        balance NUMERIC(100, 2) NOT NULL,
        PRIMARY KEY(id)
    );
    CREATE TABLE ottobroker.faketransactiontypes(
        id serial NOT NULL,
        txtype varchar(256) NOT NULL,
        PRIMARY KEY(id)
    );
    CREATE TABLE ottobroker.faketransactions(
        id serial NOT NULL,
        txtypeid int NOT NULL,
        userid varchar(256) NOT NULL,
        dollaramount NUMERIC(100, 2) NOT NULL,
        stockamount int NOT NULL,
        ticker varchar(10),
        executed TIMESTAMP NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY(txtypeid) REFERENCES ottobroker.faketransactiontypes(id),
        FOREIGN KEY(userid) REFERENCES ottobroker.users(id)
    );
    CREATE TABLE ottobroker.fakestocktypes(
        id serial NOT NULL,
        stocktype varchar(256) NOT NULL,
        PRIMARY KEY(id)
    );
    CREATE TABLE ottobroker.fakestocks(
        id serial NOT NULL,
        stocktypeid int NOT NULL,
        userid varchar(256) NOT NULL,
        txid int NOT NULL,
        ticker varchar(10) NOT NULL,
        purchase_cost NUMERIC(100, 2) NOT NULL,
        purchased TIMESTAMP NOT NULL,
        expiration TIMESTAMP,
        sell_cost NUMERIC(100, 2),
        sold TIMESTAMP, 
        PRIMARY KEY(id),
        FOREIGN KEY(stocktypeid) REFERENCES ottobroker.fakestocktypes(id),
        FOREIGN KEY(userid) REFERENCES ottobroker.users(id),
        FOREIGN KEY(txid) REFERENCES ottobroker.faketransactions(id)
    );
    CREATE TABLE ottobroker.deposits(
        id serial NOT NULL,
        userid varchar(256) NOT NULL,
        amount NUMERIC(100, 2) NOT NULL,
        reason VARCHAR(256),
        PRIMARY KEY(id),
        FOREIGN KEY(userid) REFERENCES ottobroker.userid
    );

    INSERT INTO ottobroker.faketransactiontypes (txtype) values ('BUY'), ('SELL'), ('CAPITAL');
    INSERT INTO ottobroker.fakestocktypes (stocktype) values ('REGULAR');

CREATE OR REPLACE FUNCTION CreateUser(_user_id varchar(256), _display_name varchar(256))
RETURNS varchar(256) AS $BODY$
    DECLARE
        user_exists int = 0;
        result_id varchar(256) = Null;
    BEGIN
        select count(id) into user_exists from ottobroker.users where id = _user_id;
        if user_exists <= 0 THEN
            insert into ottobroker.users (id, displayname, created, balance)
            values (_user_id, _display_name, now(), 0) returning id into result_id;
            perform GiveMoney(_user_id, 10000.00);
        end if;
        return result_id;
    END;
    $BODY$
LANGUAGE 'plpgsql' VOLATILE;

CREATE OR REPLACE FUNCTION GiveMoney(_user_id varchar(256), _amount numeric(100, 2))
RETURNS int AS $BODY$
    DECLARE
        user_exists int = 0;
        user_balance numeric(100, 2) = 0;
        txtype_id int = -1;
        transaction_id int = null;
    BEGIN
        select count(id) into user_exists from ottobroker.users where id = _user_id;
        if user_exists = 1 THEN
            select balance into user_balance from ottobroker.users where id =_user_id;
            update ottobroker.users set balance = user_balance + _amount where id = _user_id;
            select id into txtype_id from ottobroker.faketransactiontypes where txtype = 'CAPITAL';
            insert into ottobroker.faketransactions (txtypeid, userid, dollaramount, stockamount, executed)
            values (txtype_id, _user_id, _amount, 0, now()) returning id into transaction_id;
        end if;
        return transaction_id;
    END;
    $BODY$
LANGUAGE 'plpgsql' VOLATILE;

CREATE OR REPLACE FUNCTION BuyRegularStock(_ticker varchar(10), _quantity int, _per_cost numeric(100, 2), _user_id varchar(256))
RETURNS INTEGER AS $BODY$
    DECLARE
        total_cost numeric(100, 2) = -1;
        user_balance numeric(100, 2) = -1;
        stock_index int = -1;
        transaction_id int = null;
        txtype_id int = -1;
        stocktype_id int = -1;
        _now timestamp = now();
    BEGIN
        select balance into user_balance from ottobroker.users where id = _user_id;
        total_cost := _quantity * _per_cost;
        if user_balance >= total_cost THEN
            update ottobroker.users set balance = user_balance - total_cost where id = _user_id;
            select id into txtype_id from ottobroker.faketransactiontypes where txtype = 'BUY';
            select id into stocktype_id from ottobroker.fakestocktypes where stocktype = 'REGULAR';
            insert into ottobroker.faketransactions (txtypeid, userid, dollaramount, stockamount, ticker, executed)
            values (txtype_id, _user_id, total_cost, _quantity, _ticker, _now) returning id into transaction_id;
            for i in 1.._quantity LOOP
            	insert into ottobroker.fakestocks (stocktypeid, userid, txid, ticker, purchase_cost, purchased)
                values (stocktype_id, _user_id, transaction_id, _ticker, _per_cost, _now);
            end loop;
        end if;
        return transaction_id;
    END;
    $BODY$
LANGUAGE 'plpgsql' VOLATILE;

CREATE OR REPLACE FUNCTION SellStock(_ticker varchar(10), _quantity int, _per_value numeric(100, 2), _user_id varchar(256))
RETURNS INTEGER AS $BODY$
    DECLARE
        total_value numeric(100, 2) = -1;
        user_balance NUMERIC(100, 2) = -1;
        stock_count int = -1;
        transaction_id int = -1;
        txtype_id int = null;
        stock_id int = 0;
        _now timestamp = now();
    BEGIN
        select count(id) into stock_count from ottobroker.fakestocks where userid = _user_id AND ticker = _ticker;
        if stock_count >= _quantity THEN
            total_value := _quantity * _per_value;
            select balance into user_balance from ottobroker.users where id = _user_id;
            update ottobroker.users set balance = user_balance + total_value where id = _user_id;
            select id into txtype_id from ottobroker.faketransactiontypes where txtype = 'SELL';
            insert into ottobroker.faketransactions (txtypeid, userid, dollaramount, stockamount, ticker, executed)
            values (txtype_id, _user_id, total_value, _quantity, _ticker, _now) returning id into transaction_id;
            for i in 1.._quantity LOOP
                select id into stock_id from ottobroker.fakestocks where userid = _user_id and sold is null and ticker = _ticker order by purchased asc limit 1;
            	update ottobroker.fakestocks set sold = _now, sell_cost = _per_value where id = stock_id;
            end loop;
        end if;
        return transaction_id;
    END;
    $BODY$
LANGUAGE 'plpgsql' VOLATILE;
