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
    after int,
    commandid int NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(commandid) REFERENCES ottobot.commands(id),
    FOREIGN KEY(after) REFERENCES ottobot.responses(id)
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
    previousresponse int NOT NULL,
    stored timestamp,
    execute timestamp NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(requestid) REFERENCES ottobot.requests(id),
    FOREIGN KEY(previousresponse) REFERENCES ottobot.responses(id)
);
INSERT INTO ottobot.commandtypes (name) values ('STARTS_WITH'), ('CONTAINS'), ('EQUALS');
