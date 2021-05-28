# -*- coding: utf-8 -*-
"""
MeSH Traslation Workflow (MTW) background worker - Flask app factory
"""
import logging
from flask import Flask, abort, request

from application import utils as mtu

def create_app(debug=False, logger=None, 
               config_path='conf/mtw.ini',
               static_url_path='/assets-mtw'):

    app = Flask(__name__, instance_relative_config=True, static_url_path=static_url_path)
    app.debug = debug
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    if logger:
        app.logger = logger
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
        APP_VER = '0.1.7',
        API_VER = '1.0.0',
        TEMP_DIR = mtu.get_instance_dir(app, 'temp'),
        local_config_file = mtu.get_instance_dir(app, config_path)
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


    @app.route('/export_data/get:<export>', methods=['GET','POST'])
    def export_data(export):

        if export in ['umls','umls_all','js_all','js_parsers','js_elastic','xml_desc','xml_qualif','marc']:

            app.logger.info('Export '+ export +' started  ...')

            if export in ['umls','umls_all']:
                mtu.exportData(export)
            else:
                if request.method == 'POST':
                    if request.json:
                        if request.json.get(export):
                            mtu.exportLookup(export, params=request.json.get(export))
                else:
                    mtu.exportLookup(export)    

            app.logger.info('Export '+ export +' finished ...')

            return 'OK'
        else:
            return 'ERROR'        

    return app    


