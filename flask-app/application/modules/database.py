# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - database ops
"""

import uuid
from sqlite3 import dbapi2 as sqlite3

from flask import flash, g
from flask import current_app as app

from application.modules.auth import hash_pwd

#  Database


def connect_db():
    rv = sqlite3.connect(app.config["DATABASE"])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    if not hasattr(g, "sqlite_db"):
        try:
            g.sqlite_db = connect_db()
            # g.sqlite_db.execute('pragma foreign_keys=on')
        except sqlite3.Error as err:
            error = "Flask get_db error : " + str(err.args[0])
            flash(error, "danger")
            app.logger.error(f"[get_db] {err}")
            return None
        else:
            return g.sqlite_db
    else:
        return g.sqlite_db


#   Inserts


def addUser(username, firstname, lastname, passwd, ugroup, phone="", email=""):
    db = get_db()
    try:
        if passwd:
            passwd = hash_pwd(passwd)

        db.execute(
            "insert into users (username, passwd, firstname, lastname, ugroup, phone, email) values (?, ?, ?, ?, ?, ?, ?)",
            [username, passwd, firstname, lastname, ugroup, phone, email],
        )
        db.commit()

    except sqlite3.Error as e:
        return "Database error : " + str(e.args[0])


def addAudit(
    username,
    userid=0,
    otype="concept",
    detail="",
    label="",
    opid="",
    dui="",
    event="",
    tstate="updated",
    params="",
):
    db = get_db()
    res = {}
    apid = str(uuid.uuid4())

    targetyear = app.config["TARGET_YEAR"]

    try:
        db.execute(
            "insert into audit (userid, username, otype, detail, label, opid, dui, event, tstate, apid, params, targetyear) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                userid,
                username,
                otype,
                detail,
                label,
                opid,
                dui,
                event,
                tstate,
                apid,
                params,
                targetyear,
            ],
        )
        db.commit()
        res["status"] = "success"
        res["apid"] = apid
        return res

    except sqlite3.Error as e:
        res["status"] = "failed"
        res["error"] = "Database error : " + str(e.args[0])
        return res


#   Updates


def updateUser(
    username, firstname, lastname, passwd, ugroup, userid, phone="", email=""
):
    db = get_db()
    try:
        if passwd:
            passwd = hash_pwd(passwd)

            db.execute(
                "update users set username = ?, firstname = ?, lastname = ?, passwd = ?, ugroup = ?, phone = ?, email = ? where id = ?",
                [username, firstname, lastname, passwd, ugroup, phone, email, userid],
            )
        else:
            db.execute(
                "update users set username = ?, firstname = ?, lastname = ?, ugroup = ?, phone = ?, email = ? where id = ?",
                [username, firstname, lastname, ugroup, phone, email, userid],
            )
        db.commit()

    except sqlite3.Error as e:
        return "Database error : " + str(e.args[0])


def updateUserTheme(userid, theme):
    db = get_db()
    try:
        if theme:
            db.execute("update users set theme = ? where id = ?", [theme, userid])
            db.commit()

    except sqlite3.Error as e:
        return "Database error : " + str(e.args[0])


def updateUserParams(userid, params):
    db = get_db()
    try:
        db.execute("update users set params = ? where id = ?", [params, userid])
        db.commit()

    except sqlite3.Error as e:
        return "Database error : " + str(e.args[0])


def updateAuditResolved(apid, tstate="", resolvedby="", note=""):
    db = get_db()
    try:
        db.execute(
            "update audit set tstate = ?, resolvedby = ?, note = ? where apid = ?",
            [tstate, resolvedby, note, apid],
        )
        db.commit()

    except sqlite3.Error as e:
        return "Database error : " + str(e.args[0])


#   Selects


def getUserPwd(username):
    db = get_db()
    query = "select passwd from users " "  where username = :username limit 1 "
    if db:
        db.row_factory = dict_factory
        cur = db.cursor()
        cur = db.execute(query, {"username": username})
        return cur.fetchone()


def getUserData(userid=None, username=None):
    db = get_db()
    query = None
    if username:
        query = (
            "select id, firstname, lastname, ugroup, theme, params, updated from users "
            "  where username = :username limit 1 "
        )
        params = {"username": username}

    if userid == 0:
        userid = "0"

    if userid:
        query = (
            "select id, firstname, lastname, ugroup, theme, params, updated from users "
            "  where id = :userid limit 1 "
        )
        params = {"userid": userid}

    if db and query:
        db.row_factory = dict_factory
        cur = db.cursor()
        cur = db.execute(query, params)
        return cur.fetchone()


def getUsers(userid=None):
    db = get_db()
    params = {}
    if userid:
        query = (
            "select id, username, firstname, lastname, ugroup, phone, email, updated from users "
            " where id = :userid limit 1 "
        )
        params["userid"] = userid
    else:
        query = "select id, username, firstname, lastname, ugroup, phone, email, updated from users order by id"

    if db:
        db.row_factory = dict_factory
        cur = db.execute(query, params)
        return cur.fetchall()


# sqlite view:  audit_targetyear
def getTargetYears():
    db = get_db()
    if db:
        db.row_factory = lambda cursor, row: row[0]
        cur = db.execute("select targetyear from audit_targetyear")
        db.row_factory = dict_factory
        return cur.fetchall()


# sqlite view:  audit_created_yr_mon | audit_resolved_yr_mon
def getReportMonth(targetyear=None):
    db = get_db()
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        db.row_factory = lambda cursor, row: row[0]
        query = (
            "select yr_mon from audit_created_yr_mon "
            " where targetyear = :targetyear "
            " union "
            "select yr_mon from audit_resolved_yr_mon "
            " where targetyear = :targetyear "
            " order by yr_mon "
        )
        params = {"targetyear": targetyear}
        cur = db.execute(query, params)
        db.row_factory = dict_factory
        return cur.fetchall()


# sqlite view:  audit_event
def getAuditEvent(targetyear=None):
    db = get_db()
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        query = (
            "select event, cnt from audit_event "
            " where targetyear = :targetyear order by event "
        )
        params = {"targetyear": targetyear}
        cur = db.execute(query, params)
        return cur.fetchall()


# sqlite view:  audit_tstate
def getAuditStatus(targetyear=None):
    db = get_db()
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        query = (
            "select tstate, cnt from audit_tstate "
            " where targetyear = :targetyear order by tstate "
        )
        params = {"targetyear": targetyear}
        cur = db.execute(query, params)
        return cur.fetchall()


# sqlite view:  audit_event_tstate
def getAuditEventStatus(event, targetyear=None):
    db = get_db()
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        query = (
            "select event, tstate, cnt from audit_event_tstate "
            "  where targetyear = :targetyear and event = :event order by tstate "
        )
        params = {"targetyear": targetyear, "event": event}
        cur = db.execute(query, params)
        return cur.fetchall()


# sqlite view:  audit_users_tstate
def getAuditUserStatus(userid="", tstate="", targetyear=None, route=None):
    db = get_db()
    userid = str(userid)
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        query = "select userid, username, tstate, ugroup, cnt from audit_users_tstate "
        where = " where userid > -1 and targetyear = :targetyear "
        tail = " order by username, tstate "
        params = {}
        params["targetyear"] = targetyear

        if not userid and not tstate:
            if route == "approve":
                query = "select distinct userid, username, ugroup from audit_users_tstate where targetyear = :targetyear order by username "
                cur = db.execute(query, params)
                return cur.fetchall()
            else:
                query = "select tstate, cnt from audit_tstate where targetyear = :targetyear order by tstate "
                cur = db.execute(query, params)
                return cur.fetchall()

        if userid:
            where += " and userid = :userid "
            params["userid"] = userid

        if tstate:
            where += " and tstate = :tstate "
            params["tstate"] = tstate

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


# sqlite view:  audit_users_event
def getAuditUsersEvent(event, userid="", tstate="", targetyear=None, route=None):
    db = get_db()
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        query = "select userid, username, event, tstate, ugroup, cnt from audit_users_event "
        where = " where targetyear = :targetyear and event = :event "
        tail = " order by username, tstate "
        params = {}
        params["targetyear"] = targetyear
        params["event"] = event

        if not userid and not tstate:
            query = (
                "select event, cnt from audit_event "
                " where targetyear = :targetyear and event = :event order by event"
            )
            cur = db.execute(query, params)
            return cur.fetchall()

        if tstate:
            where += " and tstate = :tstate "
            params["tstate"] = tstate

        if userid:
            where += " and userid = :userid "
            params["userid"] = userid

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getAuditForItem(dui, cui=None, targetyear=None):
    db = get_db()
    if db:
        db.row_factory = dict_factory
        query = "select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, resolvedby, note from audit "
        tail = " order by id "
        params = {}
        params["dui"] = dui

        if cui:
            where = " where dui = :dui and opid = :cui "
            params["cui"] = cui
        else:
            where = " where dui = :dui "

        if targetyear:
            where += " and targetyear = :targetyear "
            params["targetyear"] = targetyear

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getAuditLocked(dui):
    db = get_db()
    if db:
        db.row_factory = dict_factory
        q = (
            "select apid from audit "
            "  where dui = :dui and event = 'lock' and tstate = 'locked' and otype = 'descriptor' limit 1 "
        )
        cur = db.cursor()
        cur = db.execute(q, {"dui": dui})
        return cur.fetchone()


def getAuditRecord(apid):
    db = get_db()
    qr_udata = (
        "select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, resolvedby, note from audit "
        "  where apid = :apid limit 1 "
    )
    if db:
        db.row_factory = dict_factory
        cur = db.cursor()
        cur = db.execute(qr_udata, {"apid": apid})
        return cur.fetchone()


def getAuditPending(tstate="pending", userid=None, event=None, sort="asc", limit=500):
    db = get_db()
    if db:
        db.row_factory = dict_factory
        if limit > 500:
            limit = 500

        query = "select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, note from audit "
        where = " where tstate = :tstate "
        tail = " order by id " + sort + " limit " + str(limit)
        params = {}
        params["tstate"] = tstate

        if userid == 0:
            userid = "0"

        if userid:
            where += " and userid = :userid "
            params["userid"] = userid

        if event:
            where += " and event = :event "
            params["event"] = event

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getAuditResolved(
    userid,
    tstate=None,
    event=None,
    resolvedby=None,
    sort="desc",
    targetyear=None,
    limit=500,
):
    db = get_db()
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        db.row_factory = dict_factory
        if limit > 500:
            limit = 500

        query = "select dui, opid, userid, username, targetyear, event, tstate, otype, apid, detail, label, created, updated, params, resolvedby, note from audit "
        where = ' where targetyear = :targetyear and userid = :userid and otype in ("concept","descriptor") '
        tail = " order by updated " + sort + " limit " + str(limit)
        params = {}
        params["targetyear"] = targetyear
        params["userid"] = userid

        if tstate:
            where += " and tstate = :tstate "
            params["tstate"] = tstate
        else:
            where += ' and tstate in ("approved","rejected") '
            params["tstate"] = tstate

        if resolvedby:
            where += " and resolvedby = :resolvedby "
            params["resolvedby"] = resolvedby

        if event:
            where += " and event = :event "
            params["event"] = event

        q = query + where + tail
        cur = db.execute(q, params)
        return cur.fetchall()


def getReport(view=None, targetyear=None, userid=None, mon=None):
    db = get_db()
    if not targetyear:
        targetyear = app.config["TARGET_YEAR"]
    if db:
        db.row_factory = dict_factory

        if view == "resolved":
            base_query = "SELECT yr_mon, userid, username, event, tstate, cnt, targetyear FROM audit_resolved"
        else:
            base_query = "SELECT yr_mon, userid, username, event, tstate, cnt, targetyear FROM audit_created"

        conditions = ["targetyear = :targetyear"]
        params = {"targetyear": targetyear}

        if userid:
            conditions.append("userid = :userid")
            params["userid"] = userid

        if mon:
            conditions.append("yr_mon = :mon")
            params["mon"] = mon

        where_clause = " WHERE " + " AND ".join(conditions)
        order_clause = " ORDER BY yr_mon, userid, event, tstate"

        # safe: no user input in query
        # params = {"targetyear": targetyear, "userid": userid, "mon": mon}
        query = base_query + where_clause + order_clause
        cur = db.execute(query, params)
        return cur.fetchall()


#   Deletes


def deleteUser(userid):
    db = get_db()
    try:
        db.execute("delete from users where id = ? ", [userid])
        db.commit()

    except sqlite3.Error as e:
        return "Database error : " + str(e.args[0])


# Functions


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
