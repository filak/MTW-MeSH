-- version 0.2.2
-- run:  sqlite3 mtw.db < mtw_schema.sql

/* users */
--drop table if exists users;
create table users (
  id integer primary key autoincrement,
  username text unique,
  passwd text not null,
  firstname text,
  lastname text,
  ugroup text,
  email text,
  phone text,
  theme text,
  created text DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now', 'localtime')),
  updated text DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now', 'localtime')),
  params text
);

CREATE TRIGGER users_upd_trig AFTER UPDATE ON users
 BEGIN
  update users SET updated = strftime('%Y-%m-%dT%H:%M:%S','now', 'localtime') WHERE id = NEW.id;
 END;

DROP INDEX if exists i_users;
CREATE INDEX i_users ON users (id, username, passwd);


/* audit */
--drop table if exists audit;
create table audit (
  id integer primary key autoincrement,
  userid integer not null,
  username text not null,
  targetyear integer not null, -- YYYY (TARGET_YEAR from config)
  event text not null,  -- login, logout, create, update, delete, purge, export, lock, insert ...
  otype text not null,  -- object/record type:  user, concept, descriptor, data
  label text,      -- null or Concept/Descriptor label
  detail text,     -- null or event detail
  opid text,       -- null or object ID: ConceptUI or DescriptorUI or ID_username
  dui text,        -- null or object ID: DescriptorUI
  tstate text,     -- null, started, finished, failed, success | updated, pending, approved, rejected, purged, locked, unlocked
  resolvedby text, -- null or username
  note text,       -- null or editor note
  apid text,       -- null or uuid - process id
  created text DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now', 'localtime')), -- Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP  "timestamp" TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M','now', 'localtime'))
  updated text DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now', 'localtime')),
  params text      -- null or input-data or original-data
);

CREATE TRIGGER audit_upd_trig AFTER UPDATE ON audit
 BEGIN
  update audit SET updated = strftime('%Y-%m-%dT%H:%M:%S','now', 'localtime') WHERE id = NEW.id;
 END;

DROP INDEX if exists i_audit;
CREATE INDEX i_audit ON audit (id, userid, username, event, otype, opid, dui, tstate, created, resolvedby, targetyear);


/* Views */
--select name from sqlite_master where type in ('view');

drop view audit_targetyear;
create view audit_targetyear as select distinct targetyear from audit
       where otype in ('concept','descriptor') order by targetyear;

drop view audit_tstate;
create view audit_tstate as select targetyear, tstate, count(*) as cnt from audit where otype in ('concept','descriptor') group by targetyear, tstate;

drop view audit_userid_tstate;
create view audit_userid_tstate as select targetyear, userid, tstate, count(*) as cnt from audit where otype in ('concept','descriptor') group by targetyear, userid, tstate;

drop view audit_users_tstate;
create view audit_users_tstate as select *,
           (select username from users where id = A.userid) username,
           (select ugroup from users where id = A.userid) ugroup
           from audit_userid_tstate A;


drop view audit_userid_tstate_event;
create view audit_userid_tstate_event as select targetyear, userid, tstate, event, count(*) as cnt from audit where otype in ('concept','descriptor') group by targetyear, userid, tstate, event;

drop view audit_users_event;
create view audit_users_event as select *,
           (select username from users where id = A.userid) username,
           (select ugroup from users where id = A.userid) ugroup
           from audit_userid_tstate_event A;

drop view audit_event;
create view audit_event as select targetyear, event, count(*) as cnt from audit where otype in ('concept','descriptor') group by targetyear, event;

drop view audit_event_tstate;
create view audit_event_tstate as select targetyear, event, tstate, count(*) as cnt from audit where otype in ('concept','descriptor') group by targetyear, event, tstate;


drop view audit_created_yr_mon;
create view audit_created_yr_mon as select targetyear,
       strftime('%Y-%m', created) as yr_mon, count(*) as cnt from audit
       where otype in ('concept','descriptor') group by targetyear, yr_mon;

drop view audit_created_userid;
create view audit_created_userid as select targetyear, userid, tstate, event,
       strftime('%Y-%m', created) as yr_mon, count(*) as cnt from audit
       where otype in ('concept','descriptor') group by targetyear, yr_mon, userid, tstate, event;

drop view audit_created;
create view audit_created as select *,
           (select username from users where id = A.userid) username
           from audit_created_userid A;


drop view audit_resolved_yr_mon;
create view audit_resolved_yr_mon as select targetyear,
       strftime('%Y-%m', updated) as yr_mon, count(*) as cnt from audit
       where otype in ('concept','descriptor') and tstate in ('approved','rejected') group by targetyear, yr_mon;

drop view audit_resolved_username;
create view audit_resolved_username as select targetyear, resolvedby as username, tstate, event,
       strftime('%Y-%m', updated) as yr_mon, count(*) as cnt from audit
       where otype in ('concept','descriptor') and tstate in ('approved','rejected') group by targetyear, yr_mon, username, tstate, event;

drop view audit_resolved;
create view audit_resolved as select *,
           (select id from users where username = A.username) userid
           from audit_resolved_username A;

/*
-- TODO:
drop view audit_login;
create view audit_login as select userid, username, event, strftime('%Y-%m-%d %H:%M', created) as crt
            from audit where otype = 'user' and event = 'login'
            and strftime('%Y-%m-%d', created) = strftime('%Y-%m-%d','now', 'localtime');

drop view audit_logout;
create view audit_logout as select userid, username, event, strftime('%Y-%m-%d %H:%M', created) as crt
            from audit where otype = 'user' and event = 'logout'
            and strftime('%Y-%m-%d', created) = strftime('%Y-%m-%d','now', 'localtime');
*/
