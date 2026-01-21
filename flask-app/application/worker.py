# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) background worker - Flask app factory
"""

import os
from flask import Flask

from application.modules import utils as mtu


def create_app(
    debug=False,
    port=5903,
    config_path="conf/mtw.ini",
    server_name=None,
    relax=False,
):

    app = Flask(__name__, instance_relative_config=True)

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
            APP_NAME="MTW Worker",
            APP_VER="0.1.10",
            API_VER="1.0.0",
            TEMP_DIR=mtu.get_instance_dir(app, "temp"),
            local_config_file=mtu.get_instance_dir(app, config_path),
            admin_config_file=mtu.get_instance_dir(app, "conf/mtw-admin.tmp"),
        )
    )

    app.app_context().push()

    adminConfig = mtu.getConfig(app.config["admin_config_file"], admin=True)

    if not adminConfig:
        return

    d = mtu.getAdminConfValue(adminConfig, worker_only=True)

    if not d:
        return

    app.config.update(d)

    localConfig = mtu.getConfig(app.config["local_config_file"])

    if not localConfig:
        return

    d = mtu.getLocalConfValue(localConfig)

    if not d:
        return

    app.config.update(d)

    # Server settings

    app.config.update({"APP_HOST": app.config.get("SERVER_NAME")})
    app.config.update({"SERVER_NAME": None})

    if app.debug:
        print("Worker host: ", app.config["WORKER_HOST"])

    if relax:
        app.config.update({"APP_RELAXED": True})

    from application.modules.worker_api import endpoints  # noqa: F401

    return app
