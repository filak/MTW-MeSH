# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - database ops
"""
import uuid
from sqlite3 import dbapi2 as sqlite3

from flask import current_app as app

###   Inserts

def addUser(db, username, firstname, lastname, passwd, ugroup, phone='', email=''):
    try:
        db.execute('insert into users (username, passwd, firstname, lastname, ugroup, phone, email) values (?, ?, ?, ?, ?, ?, ?)',
                  [username, passwd, firstname, lastname, ugroup, phone, email])
        db.commit()

    except sqlite3.Error as e:
        return 'Database error : '+str(e.args[0])


def addAudit(db, username, userid=0, otype='concept', detail='', label='', opid='', dui='', event='', tstate='updated', params=''):
    res = {}
    apid = str(uuid.uuid4())

    targetyear = app.config['TARGET_YEAR']

    try:
        db.execute('insert into audit (userid, username, otype, detail, label, opid, dui, event, tstate, apid, params, targetyear) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                      [userid, username, otype, detail, label, opid, dui, event, tstate, apid, params, targetyear])
        db.commit()
        res['status'] = 'success'
        res['apid'] = apid
        return res

    except sqlite3.Error as e:
        res['status'] = 'failed'
        res['error'] = 'Database error : ' + str(e.args[0])
        return res


###   Updates

def updateUser(db, username, firstname, lastname, passwd, ugroup, userid, phone='', email=''):
    try:
        if passwd:
            db.execute('update users set username = ?, firstname = ?, lastname = ?, passwd = ?, ugroup = ?, phone = ?, email = ? where id = ?',
                  [username, firstname, lastname, passwd, ugroup, phone, email, userid])
        else:
            db.execute('update users set username = ?, firstname = ?, lastname = ?, ugroup = ?, phone = ?, email = ? where id = ?',
                  [username, firstname, lastname, ugroup, phone, email, userid])
        db.commit()

    except sqlite3.Error as e:
        return 'Database error : '+str(e.args[0])


def updateUserTheme(db, userid, theme):
    try:
        if theme:
            db.execute('update users set theme = ? where id = ?',
                       [theme, userid])
            db.commit()

    except sqlite3.Error as e:
        return 'Database error : '+str(e.args[0])


def updateUserParams(db, userid, params):
    try:
        db.execute('update users set params = ? where id = ?',
                   [params, userid])
        db.commit()

    except sqlite3.Error as e:
        return 'Database error : '+str(e.args[0])


def updateAuditResolved(db, apid, tstate='', resolvedby='', note=''):
    try:
        db.execute('update audit set tstate = ?, resolvedby = ?, note = ? where apid = ?',
                   [tstate, resolvedby, note, apid])
        db.commit()

    except sqlite3.Error as e:
        return 'Database error : '+str(e.args[0])


###   Selects

def getUserPwd(db, username):
    query = ('select passwd from users '
                '  where username = :username limit 1 ')
    if db:
        db.row_factory = dict_factory
        cur = db.cursor()
        cur = db.execute(query, {'username': username} )
        return cur.fetchone()


def getUserData(db, userid=None, username=None):
    query = None
    if username:
        query = ('select id, firstname, lastname, ugroup, theme, params, updated from users '
                    '  where username = :username limit 1 ')
        params = {'username': username}

    if userid == 0:
        userid = '0'

    if userid:
        query = ('select id, firstname, lastname, ugroup, theme, params, updated from users '
                    '  where id = :userid limit 1 ')
        params = {'userid': userid}

    if db and query:
        db.row_factory = dict_factory
        cur = db.cursor()
        cur = db.execute(query, params)
        return cur.fetchone()


def getUsers(db, userid=None):
    params = {}
    if userid:
        query = ('select id, username, firstname, lastname, ugroup, phone, email, updated from users '
                 ' where id = :userid limit 1 ')
        params['userid'] = userid
    else:
        query = ('select id, username, firstname, lastname, ugroup, phone, email, updated from users order by id')

    if db:
        db.row_factory = dict_factory
        cur = db.execute(query, params)
        return cur.fetchall()


### sqlite view:  audit_targetyear
def getTargetYears(db):
    if db:
        db.row_factory = lambda cursor, row: row[0]
        cur = db.execute('select targetyear from audit_targetyear')
        db.row_factory = dict_factory
        return cur.fetchall()


### sqlite view:  audit_created_yr_mon | audit_resolved_yr_mon
def getReportMonth(db, targetyear=None):
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        db.row_factory = lambda cursor, row: row[0]
        query = ('select yr_mon from audit_created_yr_mon '
                 ' where targetyear = :targetyear '
                 ' union '
                 'select yr_mon from audit_resolved_yr_mon '
                 ' where targetyear = :targetyear '
                 ' order by yr_mon '
                 )
        params = {'targetyear': targetyear}
        cur = db.execute(query, params)
        db.row_factory = dict_factory
        return cur.fetchall()


### sqlite view:  audit_event
def getAuditEvent(db, targetyear=None):
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        query = ('select event, cnt from audit_event '
                 ' where targetyear = :targetyear order by event ')
        params = {'targetyear': targetyear}
        cur = db.execute(query, params)
        return cur.fetchall()


### sqlite view:  audit_tstate
def getAuditStatus(db, targetyear=None):
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        query = ('select tstate, cnt from audit_tstate '
                 ' where targetyear = :targetyear order by tstate ')
        params = {'targetyear': targetyear}
        cur = db.execute(query, params)
        return cur.fetchall()


### sqlite view:  audit_event_tstate
def getAuditEventStatus(db, event, targetyear=None):
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        query = ('select event, tstate, cnt from audit_event_tstate '
                    '  where targetyear = :targetyear and event = :event order by tstate ')
        params = {'targetyear': targetyear, 'event': event}
        cur = db.execute(query, params)
        return cur.fetchall()


### sqlite view:  audit_users_tstate
def getAuditUserStatus(db, userid='', tstate='', targetyear=None, route=None):
    userid = str(userid)
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        query = 'select userid, username, tstate, ugroup, cnt from audit_users_tstate '
        where = ' where userid > -1 and targetyear = :targetyear '
        tail =  ' order by username, tstate '
        params = {}
        params['targetyear'] = targetyear

        if not userid and not tstate:
            if route == 'approve':
                query = 'select distinct userid, username, ugroup from audit_users_tstate where targetyear = :targetyear order by username '
                cur = db.execute(query, params)
                return cur.fetchall()
            else:    
                query = 'select tstate, cnt from audit_tstate where targetyear = :targetyear order by tstate '
                cur = db.execute(query, params)
                return cur.fetchall()

        if userid:
            where += ' and userid = :userid '
            params['userid'] = userid

        if tstate:
            where += ' and tstate = :tstate '
            params['tstate'] = tstate

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


### sqlite view:  audit_users_event
def getAuditUsersEvent(db, event, userid='', tstate='', targetyear=None, route=None):
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        query = 'select userid, username, event, tstate, ugroup, cnt from audit_users_event '
        where = ' where targetyear = :targetyear and event = :event '
        tail =  ' order by username, tstate '
        params = {}
        params['targetyear'] = targetyear
        params['event'] = event

        if not userid and not tstate:
            query = ('select event, cnt from audit_event '
                     ' where targetyear = :targetyear and event = :event order by event')
            cur = db.execute(query, params)
            return cur.fetchall()

        if tstate:
            where += ' and tstate = :tstate '
            params['tstate'] = tstate

        if userid:
            where += ' and userid = :userid '
            params['userid'] = userid

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getAuditForItem(db, dui, cui=None, targetyear=None):
    if db:
        db.row_factory = dict_factory
        query = 'select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, resolvedby, note from audit '
        tail =  ' order by id '
        params = {}
        params['dui'] = dui

        if cui:
            where = ' where dui = :dui and opid = :cui '
            params['cui'] = cui
        else:
            where = ' where dui = :dui '

        if targetyear:
            where += ' and targetyear = :targetyear '
            params['targetyear'] = targetyear

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getAuditLocked(db, dui):
    if db:
        db.row_factory = dict_factory
        q = ('select apid from audit '
            '  where dui = :dui and event = \'lock\' and tstate = \'locked\' and otype = \'descriptor\' limit 1 ')
        cur = db.cursor()
        cur = db.execute(q, {'dui': dui} )
        return cur.fetchone()


def getAuditRecord(db, apid):
    qr_udata = ('select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, resolvedby, note from audit '
                '  where apid = :apid limit 1 ')
    if db:
        db.row_factory = dict_factory
        cur = db.cursor()
        cur = db.execute(qr_udata, {'apid': apid} )
        return cur.fetchone()


def getAuditPending(db, tstate='pending', userid=None, event=None, sort='asc', limit=500):
    if db:
        db.row_factory = dict_factory
        if limit > 500:
            limit = 500

        query = 'select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, note from audit '
        where = ' where tstate = :tstate '
        tail =  ' order by id ' + sort + ' limit ' + str(limit)
        params = {}
        params['tstate'] = tstate

        if userid == 0:
            userid = '0'

        if userid:
            where += ' and userid = :userid '
            params['userid'] = userid

        if event:
            where += ' and event = :event '
            params['event'] = event            

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getAuditResolved(db, userid, tstate=None, event=None, resolvedby=None, sort='desc', targetyear=None, limit=500):
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        db.row_factory = dict_factory
        if limit > 500:
            limit = 500

        query = 'select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, resolvedby, note from audit '
        where = ' where targetyear = :targetyear and userid = :userid and otype in ("concept","descriptor") '
        tail =  ' order by updated ' + sort + ' limit ' + str(limit)
        params = {}
        params['targetyear'] = targetyear
        params['userid'] = userid

        if tstate:
            where += ' and tstate = :tstate '
            params['tstate'] = tstate
        else:
            where += ' and tstate in ("approved","rejected") '
            params['tstate'] = tstate

        if resolvedby:
            where += ' and resolvedby = :resolvedby '
            params['resolvedby'] = resolvedby

        if event:
            where += ' and event = :event '
            params['event'] = event

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getReport(db, view, targetyear=None, userid=None, mon=None):
    if not targetyear:
        targetyear = app.config['TARGET_YEAR']
    if db:
        db.row_factory = dict_factory

        query = 'select yr_mon, userid, username, event, tstate, cnt, targetyear from audit_' + view
        where = ' where targetyear = :targetyear '
        tail =  ' order by yr_mon, userid, event, tstate '
        params = {}
        params['targetyear'] = targetyear

        if userid:
            params['userid'] = userid
            where += ' and userid = :userid '

        if mon:
            params['mon'] = mon
            where += ' and yr_mon = :mon '

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


###   Deletes

def deleteUser(db, userid):
    try:
        db.execute('delete from users where id = ? ', [userid])
        db.commit()

    except sqlite3.Error as e:
        return 'Database error : '+str(e.args[0])


### Functions

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
