# -*- coding: utf-8 -*-
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 55930
DEFAULT_THREADS = 64
DEFAULT_CONFIG = 'conf/mtw-dist.ini'

import os, sys, argparse, logging
from application import create_app
from waitress import serve

appname    = 'mtw-server'
appdesc    = 'MTW Server 1.4.12'
appusage   = 'Help:  ' + appname + ' -h \n'
appauthor  = 'Filip Kriz'

def main():
    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s [options]')
    parser.add_argument('--config', type=str, help='Config file path - default: '+DEFAULT_CONFIG, default=DEFAULT_CONFIG)
    parser.add_argument('--host', type=str, help='Host - default: '+DEFAULT_HOST, default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, help='Port number - default: '+str(DEFAULT_PORT), default=DEFAULT_PORT)
    parser.add_argument('--threads', type=int, help='Number of threads - default: '+str(DEFAULT_THREADS), default=DEFAULT_THREADS)
    parser.add_argument('--debug', help='Run in debug mode - DO NOT use in production !', action='store_true')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('\nERROR : Uknown arguments : ', unknown)
        print('Try help : py ' + appname  + '.py -h')
        return

    logger = logging.getLogger('waitress')

    if args.debug:
        debug = True
    else:
        debug = False

    app = create_app(debug=debug, logger=logger, config_path=args.config)

    if getattr(sys, 'frozen', False):
        app.static_folder = os.path.join(os.path.dirname(sys.executable), 'static')
        app.template_folder = os.path.join(os.path.dirname(sys.executable), 'templates')

    try:
        serve(app, host=args.host, port=args.port, threads=args.threads)
        #serve(app, listen=args.host+':'+str(args.port), threads=args.threads)

    except:
        print('Server cannot be started - check/modify the args')

if __name__ == "__main__":
    main()
    