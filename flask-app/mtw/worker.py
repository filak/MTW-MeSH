# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) - Flask background worker
"""
import time, pprint
from sqlite3 import dbapi2 as sqlite3
from flask import Flask

from mtw_database import mtw_db as mdb
from mtw_utils import mtw_utils as mtu

app = Flask(__name__, instance_relative_config=True, static_url_path='/assets-mtw')
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

pp = pprint.PrettyPrinter(indent=2)

if not app.debug:
    import logging
    from logging import FileHandler
    from logging import Formatter
    file_handler = FileHandler(mtu.get_instance_dir(app, 'logs/mtw_worker.log'))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '))
    app.logger.addHandler(file_handler)

app.config.update(dict(
    APP_NAME = 'MTW Worker',
    APP_VER = '0.1.6',
    API_VER = '1.0.0',
    TEMP_DIR = mtu.get_instance_dir(app, 'temp'),
    local_config_file = mtu.get_instance_dir(app, 'conf/mtw.ini'),
    admin_config_file = mtu.get_instance_dir(app, 'conf/mtw-admin.tmp')
))

localConfig = mtu.getConfig(app.config['local_config_file'])
if localConfig:
    with app.app_context():
        d = mtu.getLocalConfValue(localConfig)
    app.config.update(d)
else:
    error = 'Error reading local config file: ' + app.config['local_config_file']
    app.logger.error(error)
    abort(500)

adminConfig = mtu.getConfig(app.config['admin_config_file'])
if adminConfig:
    with app.app_context():
        d = mtu.getAdminConfValue(adminConfig)
    app.config.update(d)
else:
    error = 'No admin config file: ' + app.config['admin_config_file'] + '\nPlease, run the set-mtw-admin tool...\n\n'
    app.logger.error(error)
    print(error)
    abort(503)


@app.route('/')
def hello_world():
    return 'MTW worker'


@app.route('/refresh_stats/get:<stat>', methods=['GET','POST'])
def refresh_stats(stat):

    if stat in ['initial','actual','all','duplicates','lookups','lookups_rest']:

        app.logger.info('Stats gen started  ...')
        mtu.refreshStats(stat)
        app.logger.info('Stats gen finished ...')

        return 'OK'
    else:
        return 'ERROR'


@app.route('/export_data/get:<export>', defaults={'params': ''}, methods=['GET','POST'])
@app.route('/export_data/get:<export>/params:<params>', methods=['GET','POST'])
def export_data(export, params):

    if export in ['umls','umls_all','js_all','js_parsers','js_elastic','xml_desc','xml_qualif','marc']:

        app.logger.info('Export '+ export +' started  ...')

        if export in ['umls','umls_all']:
            mtu.exportData(export)
        else:
            mtu.exportLookup(export, params=params)

        app.logger.info('Export '+ export +' finished ...')

        return 'OK'
    else:
        return 'ERROR'

