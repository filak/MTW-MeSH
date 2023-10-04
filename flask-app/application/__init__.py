# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - Flask app factory
"""
import datetime, logging, pprint
from flask import Flask, abort
from pyuca import Collator

coll = Collator()
pp = pprint.PrettyPrinter(indent=2)

from application.extensions import Talisman, cache, csrf, paranoid, sess
from application import utils as mtu

def create_app(debug=False, logger=None, port=None, relax=False,
               config_path='conf/mtw.ini',
               static_url_path='/assets-mtw'):

    class ReverseProxied(object):
        def __init__(self, app):
            self.app = app

        def __call__(self, environ, start_response):
            if not debug:
                environ['wsgi.url_scheme'] = 'https'

            return self.app(environ, start_response)    

    app = Flask(__name__, instance_relative_config=True, static_url_path=static_url_path)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    if debug and not app.debug:
      app.debug = debug
    if app.debug:
        print('config:', config_path, '- port:', port) 

    if logger:
        app.logger = logger
        file_handler = logging.FileHandler(mtu.get_instance_dir(app, 'logs/mtw_server.log'))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s '))
        app.logger.addHandler(file_handler)
    else:
        file_handler = logging.FileHandler(mtu.get_instance_dir(app, 'logs/mtw_server_debug.log'))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s '))
        app.logger.addHandler(file_handler)

    app.config.update(dict(
        APP_NAME = 'MTW',
        APP_VER = '1.5.2',
        API_VER = '1.0.0',
        DBVERSION = 1.0,
        TEMP_DIR = mtu.get_instance_dir(app, 'temp'),
        local_config_file = mtu.get_instance_dir(app, config_path),
        admin_config_file = mtu.get_instance_dir(app, 'conf/mtw-admin.tmp'),
        pid_counter_file = mtu.get_instance_dir(app, 'conf/pid_counter.json'),
        CACHE_DIR = mtu.get_instance_dir(app, 'cache'),
        CSRF_COOKIE_HTTPONLY = True,
        CSRF_COOKIE_TIMEOUT = datetime.timedelta(days=1),
        CSRF_COOKIE_SECURE = True,
        SESSION_COOKIE_HTTPONLY = True,
        SESSION_COOKIE_SAMESITE = 'Lax',
        SESSION_COOKIE_SECURE = True,
        SESSION_PERMANENT = False,
        SESSION_USE_SIGNER = True,
        SESSION_TYPE = 'filesystem',
        SESSION_FILE_DIR = mtu.get_instance_dir(app, 'sessions')
    ))   

    app.app_context().push()
    ### Or use: with app.app_context():    

    localConfig = mtu.getConfig(app.config['local_config_file'])
    if localConfig:
        d = mtu.getLocalConfValue(localConfig)
        app.config.update(d)
    else:
        error = 'Error reading local config file: ' + app.config['local_config_file']
        app.logger.error(error)
        abort(500)

    adminConfig = mtu.getConfig(app.config['admin_config_file'])
    if adminConfig:
        d = mtu.getAdminConfValue(adminConfig)
        app.config.update(d)
    else:
        error = '\n\nNo admin config file: ' + app.config['admin_config_file'] + '\nPlease, run the set-mtw-admin tool...\n\n'
        app.logger.error(error)
        abort(503)


    def getPath(path):
        customDir = app.config['APP_PATH']
        return(customDir+path)
    

    ###  Flask Extensions init

    ## Cache, Session
    cache.init_app(app)
    sess.init_app(app)

    ##  SeaSurf (csrf) & Talisman
    csrf.init_app(app)    

    if not relax:
        ## Paranoid
        paranoid.init_app(app)
        paranoid.redirect_view = getPath('/')

        talisman = Talisman(
                    app,
                    session_cookie_secure=app.config['SESSION_COOKIE_SECURE'],
                    force_https=False,
                    strict_transport_security=False,
                    content_security_policy=app.config['GCSP'],
                    content_security_policy_nonce_in=['script-src','style-src']
                )

    ### Import Flask routes etc.

    from application import routes

    return app    
