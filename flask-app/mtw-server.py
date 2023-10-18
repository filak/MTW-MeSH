# -*- coding: utf-8 -*-
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 55930
DEFAULT_THREADS = 4
DEFAULT_CONFIG = 'conf/mtw-dist.ini'
DEFAULT_PREFIX = 'mtw'

import os, sys, argparse, logging
from application import create_app
from waitress import serve

appname    = 'mtw-server'
appdesc    = 'MTW Server 1.5.5'
appusage   = 'Help:  ' + appname + ' -h \n'
appauthor  = 'Filip Kriz'

def main():
    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s [options]')
    parser.add_argument('--config', type=str, help='Config file path - default: '+DEFAULT_CONFIG, default=DEFAULT_CONFIG)
    parser.add_argument('--debug', help='Run in debug mode - DO NOT use in production !', action='store_true')
    parser.add_argument('--fqdn', type=str, help='Fully qualified domain name - MUST be in sync with config !', default=None)
    parser.add_argument('--host', type=str, help='Host - default: '+DEFAULT_HOST, default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, help='Port number - default: '+str(DEFAULT_PORT), default=DEFAULT_PORT)
    parser.add_argument('--prefix', type=str, help='Path prefix - default: '+str(DEFAULT_PREFIX), default=DEFAULT_PREFIX)
    parser.add_argument('--threads', type=int, help='Number of threads - default: '+str(DEFAULT_THREADS), default=DEFAULT_THREADS)
    parser.add_argument('--relax', help='Run in relaxed mode - DO NOT use in production !', action='store_true')

    args, unknown = parser.parse_known_args()

    if unknown:
        print('\nERROR : Uknown arguments : ', unknown)
        print('Try help : py ' + appname  + '.py -h')
        return

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.ERROR)

    app = create_app(debug=args.debug, logger=logger, 
                     config_path=args.config, 
                     url_prefix=args.prefix,
                     server_name=args.fqdn, 
                     relax=args.relax)

    if getattr(sys, 'frozen', False):
        app.static_folder = os.path.join(os.path.dirname(sys.executable), 'static')
        app.template_folder = os.path.join(os.path.dirname(sys.executable), 'templates')

    if args.prefix == '/':
        url_prefix = ''
    else:
        url_prefix = args.prefix        

    try:
        if args.debug or args.relax:
            serve(app, host=args.host, port=args.port, threads=args.threads)
        else:
            server_name = app.config['SERVER_NAME']

            serve(app, host=args.host, port=args.port, threads=args.threads, url_prefix=url_prefix,
                       url_scheme='https', ident=None, server_name=server_name)

    except:
        print('Server cannot be started - check/modify the args')

if __name__ == "__main__":
    main()
    