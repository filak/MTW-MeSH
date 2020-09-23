# -*- coding: utf-8 -*-
DEFAULT_PORT = 55930
DEFAULT_THREADS = 64
DEFAULT_CONFIG = 'conf/mtw-dist.ini'

import os, sys, argparse, logging
from application import create_app
from waitress import serve

appname    = 'mtw-server'
appversion = '1.4.0'
appdesc    = 'MTW Server'
appusage   = 'Help:  ' + appname + ' -h \n'
appauthor  = 'Filip Kriz'

def main():
    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s [options]')
    parser.add_argument('--config', type=str, help='Config file path - default: '+DEFAULT_CONFIG, default=DEFAULT_CONFIG)
    parser.add_argument('--port', type=int, help='Port number - default: '+str(DEFAULT_PORT), default=DEFAULT_PORT)
    parser.add_argument('--threads', type=int, help='Number of threads - default: '+str(DEFAULT_THREADS), default=DEFAULT_THREADS)

    args, unknown = parser.parse_known_args()

    if unknown:
        print('\nERROR : Uknown arguments : ', unknown)
        print('Try help : py ' + appname  + '.py -h')
        return

    logger = logging.getLogger('waitress')

    app = create_app(debug=False, logger=logger, config_path=args.config)

    if getattr(sys, 'frozen', False):
        app.static_folder = os.path.join(os.path.dirname(sys.executable), 'static')
        app.template_folder = os.path.join(os.path.dirname(sys.executable), 'templates')

    try:
        #serve(app, host='127.0.0.1', port=args.port, threads=args.threads)
        serve(app, listen='127.0.0.1:'+str(args.port), threads=args.threads)

    except:
        print('Server cannot be started - check/modify the args')

if __name__ == "__main__":
    main()
    