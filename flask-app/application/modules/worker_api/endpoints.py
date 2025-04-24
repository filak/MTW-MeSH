from flask import request
from flask import current_app as app

from application.modules.auth import public_api_only
from application.modules import utils as mtu


@app.route('/')
def worker_index():
    return 'MTW Worker API'


@app.route('/test')
@public_api_only()
def worker_test():
    return 'MTW Worker API is NOT secured ! Debug: ' + str(app.debug)


@app.route('/refresh_stats/<stat>', methods=['GET', 'POST'])
@public_api_only()
def refresh_stats(stat):

    force = False
    if request.args.get('force'):
        force = True

    if stat in ['initial', 'actual', 'all', 'duplicates', 'lookups', 'lookups_rest']:

        app.logger.info('Stats gen started  ...')
        mtu.refreshStats(stat, force=force)
        app.logger.info('Stats gen finished ...')

        return 'OK'
    else:
        return 'ERROR'


@app.route('/export_data/<export>', methods=['GET', 'POST'])
@public_api_only()
def export_data(export):

    if export in ['umls', 'umls_all', 'umls_raw', 'js_all', 'js_parsers', 'js_elastic', 'xml_desc', 'xml_qualif', 'marc', 'training_base']:

        app.logger.info('Export ' + export + ' started  ...')

        if export in ['umls', 'umls_all', 'umls_raw', 'training_base']:
            mtu.exportData(export)
        else:
            if request.method == 'POST':
                if request.is_json:
                    if request.json.get(export):
                        mtu.exportLookup(export, params=request.json.get(export))
                else:
                    mtu.exportLookup(export)
            else:
                mtu.exportLookup(export)

        app.logger.info('Export ' + export + ' finished ...')

        return 'OK'
    else:
        return 'ERROR'
