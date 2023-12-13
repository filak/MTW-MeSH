# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - Flask app factory
"""
import datetime, logging, os, pprint
from flask import Flask, abort
from werkzeug.middleware.proxy_fix import ProxyFix
from pyuca import Collator

coll = Collator()
pp = pprint.PrettyPrinter(indent=2)

WORKER_TOKEN_HEADER = 'x-mdv-api-token'

from application.modules.extensions import Talisman, cache, csrf, paranoid, sess
from application.modules import utils as mtu

def create_app(debug=False, logger=None, port=5900, 
               config_path='conf/mtw.ini',
               server_name=None,
               url_prefix='',
               static_url_path='/assets-mtw',
               relax=False):

    url_prefix = url_prefix.strip().strip('/')

    if url_prefix:
        url_prefix = '/' + url_prefix
    else:
        url_prefix = ''    

    app = Flask(__name__, instance_relative_config=True, static_url_path=static_url_path)

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
        APPLICATION_ROOT = url_prefix,
        APP_NAME = 'MTW',
        APP_VER = '1.6.2',
        API_VER = '1.0.0',
        DBVERSION = 1.0,
        CACHE_DIR = mtu.get_instance_dir(app, 'cache'),
        CSRF_COOKIE_HTTPONLY = True,
        CSRF_COOKIE_TIMEOUT = datetime.timedelta(days=1),
        CSRF_COOKIE_SECURE = True,
        SESSION_COOKIE_HTTPONLY = True,
        SESSION_COOKIE_SAMESITE = 'Lax',
        SESSION_COOKIE_SECURE = True,
        SESSION_FILE_THRESHOLD = 1000,
        SESSION_PERMANENT = False,
        SESSION_REVERSE_PROXY = True,
        SESSION_USE_SIGNER = True,
        SESSION_TYPE = 'filesystem',
        SESSION_FILE_DIR = mtu.get_instance_dir(app, 'sessions'),
        TEMPLATES_AUTO_RELOAD = False,
        TEMP_DIR = mtu.get_instance_dir(app, 'temp'),
        local_config_file = mtu.get_instance_dir(app, config_path),
        admin_config_file = mtu.get_instance_dir(app, 'conf/mtw-admin.tmp'),
        pid_counter_file = mtu.get_instance_dir(app, 'conf/pid_counter.json')        
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


    ### Server settings

    if relax:
        app.config.update({'SERVER_NAME': None})
        app.config.update({'_RELAXED': True})      

    if app.config['SERVER_NAME']:
        app.config.update({'SESSION_COOKIE_DOMAIN': app.config['SERVER_NAME']})

    ## --fqdn <server_name>
    if server_name:
        app.config.update({'SERVER_NAME': server_name})
        app.config.update({'SESSION_COOKIE_DOMAIN': server_name}) 

    if app.config.get('SERVER_NAME'):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=0)


    ###  Flask Extensions init

    ## Cache, Session
    cache.init_app(app)
    sess.init_app(app)

    ##  SeaSurf (csrf) & Talisman
    csrf.init_app(app)    

    if not relax and not app.debug:
        ## Paranoid
        paranoid.init_app(app)
        paranoid.redirect_view = ('/')

        talisman = Talisman(
                    app,
                    session_cookie_secure=app.config['SESSION_COOKIE_SECURE'],
                    force_https=app.config['SESSION_COOKIE_SECURE'],
                    strict_transport_security=False,
                    content_security_policy=app.config['GCSP'],
                    content_security_policy_nonce_in=['script-src','style-src']
                )

    from application.modules import routes

    return app    
