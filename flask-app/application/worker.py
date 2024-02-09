# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) background worker - Flask app factory
"""
import logging, os
from flask import Flask

from application.modules import utils as mtu

def create_app(debug=False, logger=None, port=5903,
               config_path='conf/mtw.ini',
               server_name=None, 
               relax=False):   

    app = Flask(__name__, instance_relative_config=True)

    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    if debug and not app.debug:
        app.debug = debug
    elif os.getenv('FLASK_DEBUG', None):
        app.debug = True

    if app.debug:
        print('config:', config_path, '- port:', port) 

    if logger:
        app.logger = logger

    if not app.debug:
        file_handler = logging.FileHandler(mtu.get_instance_dir(app, 'logs/mtw_worker.log'))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s '))
        app.logger.addHandler(file_handler)
    else:
        file_handler = logging.FileHandler(mtu.get_instance_dir(app, 'logs/mtw_worker_debug.log'))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s '))
        app.logger.addHandler(file_handler)

    app.config.update(dict(
        APP_NAME = 'MTW Worker',
        APP_VER = '0.1.10',
        API_VER = '1.0.0',
        TEMP_DIR = mtu.get_instance_dir(app, 'temp'),
        local_config_file = mtu.get_instance_dir(app, config_path),
        admin_config_file = mtu.get_instance_dir(app, 'conf/mtw-admin.tmp')
    ))

    app.app_context().push()

    adminConfig = mtu.getConfig(app.config['admin_config_file'], admin=True)

    if not adminConfig:
        return

    d = mtu.getAdminConfValue(adminConfig, worker_only=True)

    if not d:
        return

    app.config.update(d)
          
    localConfig = mtu.getConfig(app.config['local_config_file'])

    if not localConfig:
        return

    d = mtu.getLocalConfValue(localConfig)

    if not d:
        return     

    app.config.update(d)
    
    ### Server settings

    app.config.update({'APP_HOST': app.config.get('SERVER_NAME')})
    app.config.update({'SERVER_NAME': None})  

    if relax:
        app.config.update({'APP_RELAXED': True}) 

    app.app_context().push()
    from application.modules.worker_api import endpoints

    return app

