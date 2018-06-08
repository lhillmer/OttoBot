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
    FOREIGN KEY(previousresponse) REFERENCES ottobot.responses(id)
);
INSERT INTO ottobot.commandtypes (name) values ('STARTS_WITH'), ('CONTAINS'), ('EQUALS');

CREATE TABLE ottobroker.users(
    id varchar(256) NOT NULL,
    created TIMESTAMP NOT NULL,
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
    ticker varchar(256) NOT NULL,
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
    ticker varchar(256) NOT NULL,
    acquired TIMESTAMP NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(stocktypeid) REFERENCES ottobroker.fakestocktypes(id),
    FOREIGN KEY(userid) REFERENCES ottoobroker.users(id)
);
CREATE TABLE ottobroker.deposits(
    id serial NOT NULL,
    userid varchar(256) NOT NULL,
    amount NUMERIC(100, 2) NOT NULL,
    reason VARCHAR(256),
    PRIMARY KEY(id),
    FOREIGN KEY(userid) REFERENCES ottobroker.userid
)