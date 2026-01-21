# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - Flask app factory
"""

import datetime
import os
from flask import Flask
from cachelib import FileSystemCache
from werkzeug.middleware.proxy_fix import ProxyFix

from application.modules.extensions import (
    Talisman,
    cache,
    csrf,
    paranoid,
    sess,
)  # limiter
from application.modules import utils as mtu


def create_app(
    debug=False,
    port=5900,
    config_path="conf/mtw.ini",
    server_name=None,
    url_prefix="",
    static_url_path="/assets-mtw",
    relax=False,
):

    url_prefix = url_prefix.strip().strip("/")

    if url_prefix:
        url_prefix = "/" + url_prefix
    else:
        url_prefix = "/"

    app = Flask(
        __name__, instance_relative_config=True, static_url_path=static_url_path
    )

    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    if debug and not app.debug:
        app.debug = debug
    elif os.getenv("FLASK_DEBUG", None):
        app.debug = True

    if app.debug:
        print("MTW Config:  ", config_path, " - port: ", port)

    app.config.update(
        dict(
            APPLICATION_ROOT=url_prefix,
            APP_NAME="MTW",
            APP_VER="1.7.5",
            API_VER="1.0.0",
            DBVERSION=1.0,
            CACHE_DIR=mtu.get_instance_dir(app, "cache"),
            CACHE_THRESHOLD=1000,
            CACHE_TYPE="FileSystemCache",
            CSRF_COOKIE_HTTPONLY=True,
            CSRF_COOKIE_PATH=url_prefix,
            CSRF_COOKIE_SECURE=True,
            CSRF_COOKIE_TIMEOUT=datetime.timedelta(days=1),
            CSRF_HEADER_NAME="X-CSRFToken",
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_NAME="mtw_session",
            SESSION_COOKIE_PATH=url_prefix,
            SESSION_COOKIE_SAMESITE="Lax",
            SESSION_COOKIE_SECURE=True,
            SESSION_FILE_THRESHOLD=1000,
            SESSION_IGNORE_PATHS=["/static", static_url_path],
            SESSION_KEY_PREFIX="mtws",
            SESSION_PERMANENT=False,
            PERMANENT_SESSION_LIFETIME=3600,
            SESSION_REFRESH_EACH_REQUEST=True,
            SESSION_USE_SIGNER=True,
            SESSION_TYPE="cachelib",
            SESSION_FILE_DIR=mtu.get_instance_dir(app, "sessions"),
            TEMPLATES_AUTO_RELOAD=False,
            TEMP_DIR=mtu.get_instance_dir(app, "temp"),
            local_config_file=mtu.get_instance_dir(app, config_path),
            admin_config_file=mtu.get_instance_dir(app, "conf/mtw-admin.tmp"),
            pid_counter_file=mtu.get_instance_dir(app, "conf/pid_counter.json"),
        )
    )

    app.app_context().push()

    adminConfig = mtu.getConfig(app.config["admin_config_file"], admin=True)
    if not adminConfig:
        return

    d = mtu.getAdminConfValue(adminConfig, fp=app.config["admin_config_file"])
    if not d:
        return

    app.config.update(d)

    localConfig = mtu.getConfig(app.config["local_config_file"])
    if not localConfig:
        return

    d = mtu.getLocalConfValue(localConfig, fp=app.config["local_config_file"])
    if not d:
        return

    app.config.update(d)

    # Server settings

    if relax:
        app.config.update({"SERVER_NAME": None})
        app.config.update({"_RELAXED": True})

    if app.config["SERVER_NAME"]:
        app.config.update(
            {"SESSION_COOKIE_DOMAIN": mtu.getCookieDomain(app.config["SERVER_NAME"])}
        )

    # --fqdn <server_name>
    if server_name:
        app.config.update({"SERVER_NAME": server_name})
        app.config.update({"SESSION_COOKIE_DOMAIN": mtu.getCookieDomain(server_name)})

    if app.config.get("SERVER_NAME"):
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=0, x_port=0, x_prefix=0
        )

    sess_key_prefix = app.config["SESSION_COOKIE_NAME"].replace("__Host-", "")
    app.config.update({"CSRF_COOKIE_NAME": f"{sess_key_prefix}_csrf_token"})

    if app.config["SESSION_COOKIE_NAME"].startswith("__Host-"):
        csrf_cookie_name = app.config["CSRF_COOKIE_NAME"]
        app.config.update(
            {
                "SESSION_COOKIE_DOMAIN": False,
                "SESSION_COOKIE_PATH": "/",
                "CSRF_COOKIE_DOMAIN": False,
                "CSRF_COOKIE_NAME": f"__Host-{csrf_cookie_name}",
                "CSRF_COOKIE_PATH": "/",
            }
        )

    if app.debug:
        print("Server host: ", app.config["SERVER_NAME"])
        print("Worker host: ", app.config["WORKER_HOST"])

    # Flask Extensions init

    # Cache
    cache.init_app(app)

    # Session
    app.config["SESSION_CACHELIB"] = FileSystemCache(
        cache_dir=app.config["SESSION_FILE_DIR"],
        threshold=app.config["SESSION_FILE_THRESHOLD"],
    )
    sess.init_app(app)

    # Limiter
    # limiter.init_app(app)

    # SeaSurf (csrf)
    csrf.init_app(app)

    # Talisman
    if not relax and not app.debug:
        # Paranoid
        paranoid.init_app(app)
        paranoid.redirect_view = "/"

        talisman = Talisman(  # noqa: F841
            app,
            session_cookie_secure=app.config["SESSION_COOKIE_SECURE"],
            force_https=app.config["SESSION_COOKIE_SECURE"],
            strict_transport_security=False,
            content_security_policy=app.config["GCSP"],
            content_security_policy_nonce_in=["script-src"],
        )

    from application.modules import filters  # noqa: F401
    from application.modules import routes  # noqa: F401

    return app
