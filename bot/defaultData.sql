INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$add', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$createCommand', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$deleteCommand', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$deleteResponse', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$watch', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$dumpLink', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$list', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'EQUALS';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$steamGame', FALSE, FALSE, TRUE,  id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$comedy', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'EQUALS';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$clear', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'EQUALS';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$favorite', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'EQUALS';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$xkcd', FALSE, FALSE, TRUE,  id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';
INSERT INTO ottobot.commands (text, removable, casesensitive, active, commandtypeid)
    SELECT '$stockInfo', FALSE, FALSE, TRUE, id FROM ottobot.commandtypes WHERE name = 'STARTS_WITH';

INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT 'I''m about to add some numbers', NULL, NULL, NULL, id FROM ottobot.commands WHERE text = '$add';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'add', NULL, NULL, id FROM ottobot.commands WHERE text = '$add';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT 'That was fun!', NULL, NULL, NULL, id FROM ottobot.commands WHERE text = '$add';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'create_command', NULL, NULL, id FROM ottobot.commands WHERE text = '$createCommand';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'delete_command', NULL, NULL, id FROM ottobot.commands WHERE text = '$deleteCommand';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'delete_response', NULL, NULL, id FROM ottobot.commands WHERE text = '$deleteResponse';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'get_crawl_link', NULL, NULL, id FROM ottobot.commands WHERE text = '$watch';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'get_crawl_dump_link', NULL, NULL, id FROM ottobot.commands WHERE text = '$dumpLink';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'list_commands', NULL, NULL, id FROM ottobot.commands WHERE text = '$list';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'find_steam_game', NULL, NULL, id FROM ottobot.commands WHERE text = '$steamGame';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'timing_queue', NULL, NULL, id FROM ottobot.commands WHERE text = '$comedy';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'timing_pop', NULL, NULL, id FROM ottobot.commands WHERE text = '$comedy';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'clear_chat', NULL, NULL, id FROM ottobot.commands WHERE text = '$clear';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'favorite', NULL, NULL, id FROM ottobot.commands WHERE text = '$favorite';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'find_xkcd_comic', NULL, NULL, id FROM ottobot.commands WHERE text = '$xkcd';
INSERT INTO ottobot.responses (text, functionname, next, previous, commandid)
    SELECT NULL, 'stock_data', NULL, NULL, id FROM ottobot.commands WHERE text = '$stockInfo';

UPDATE ottobot.responses
SET
    next=(SELECT id FROM ottobot.responses WHERE functionname='add')
WHERE text='I''m about to add some numbers';

UPDATE ottobot.responses
SET
    previous=(SELECT id FROM ottobot.responses WHERE text='I''m about to add some numbers'),
    next=(SELECT id FROM ottobot.responses WHERE text='That was fun!')
WHERE functionname='add';

UPDATE ottobot.responses
SET
    previous=(SELECT id FROM ottobot.responses WHERE functionname='add')
WHERE text='That was fun!';

UPDATE ottobot.responses
SET
    next=(SELECT id FROM ottobot.responses WHERE functionname='timing_pop')
WHERE functionname='timing_queue';

UPDATE ottobot.responses
SET
    previous=(SELECT id FROM ottobot.responses WHERE functionname='timing_queue')
WHERE functionname='timing_pop';
