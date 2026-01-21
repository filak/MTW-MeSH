# -*- coding: utf-8 -*-
import uuid

from flask import current_app as app
from application.modules import utils as mtu

# Filters & Context processors


@app.template_filter()
def numberFormat(value):
    return format(int(value), ",d")


@app.template_filter()
def getListSplit(value, delim="|"):
    return value.split(delim)


@app.context_processor
def cp__random_id():
    def random_id():
        return uuid.uuid4().hex[:6].upper()

    return dict(random_id=random_id)


@app.context_processor
def cp__isDbLocked():
    def isDbLocked():
        return is_lockdb()

    return dict(isDbLocked=isDbLocked)


def is_lockdb():
    lpath = mtu.getLockFpath("lockdb")
    if lpath.is_file():
        return True
    else:
        return False


@app.context_processor
def cp__getLockedBy():
    def getLockedBy(userid, uname):
        return mtu.get_locked_by(userid, uname)

    return dict(getLockedBy=getLockedBy)


@app.context_processor
def cp__hash_data():
    def hash_data(data):
        return str(hash(data))

    return dict(hash_data=hash_data)


@app.context_processor
def cp__app_state():
    def app_state():
        if app.debug:
            return "dev"
        else:
            return ""

    return dict(app_state=app_state)


@app.context_processor
def cp__get_user_params():
    def get_user_params(userid):
        return mtu.get_uparams(userid)

    return dict(get_user_params=get_user_params)


@app.context_processor
def cp__get_adminMsg():
    def get_adminMsg():
        mpath = mtu.getTempFpath("admin-msg", year=False)
        if mpath.is_file():
            return mtu.loadJsonFile(mpath)
        else:
            msg = {}
            msg["show"] = "hide"
            msg["head"] = ""
            msg["text"] = ""
            return msg

    return dict(get_adminMsg=get_adminMsg)


@app.context_processor
def cp__get_statusRep():
    def get_statusRep(status):
        return get_statRep(status)

    return dict(get_statusRep=get_statusRep)


def get_statRep(status):
    status_dict = {
        "pending": "info",
        "rejected": "danger",
        "approved": "success",
        "updated": "secondary",
        "deleted": "muted",
        "purged": "light",
        "locked": "warning",
        "unlocked": "primary",
    }
    return status_dict.get(status, "secondary")


@app.context_processor
def cp__get_userBadgeRep():
    def get_userBadgeRep(ugroup):
        return get_userRep(ugroup)

    return dict(get_userBadgeRep=get_userBadgeRep)


def get_userRep(ugroup):
    ugroup_dict = {
        "manager": "primary",
        "editor": "success",
        "contributor": "info",
        "viewer": "secondary",
        "disabled": "danger",
        "locked": "warning",
    }
    return ugroup_dict.get(ugroup, "light")


@app.context_processor
def cp__langUmls():
    def langUmls(lang):
        return mtu.getLangCodeUmls(lang)

    return dict(langUmls=langUmls)


@app.context_processor
def cp__deepGet():
    def deepGet(dictionary, keys, default=0):
        return mtu.deep_get(dictionary, keys, default=default)

    return dict(deepGet=deepGet)
