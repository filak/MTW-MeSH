# -*- coding: utf-8 -*-
import os
import sys
import argparse
import logging
from waitress import serve

from application.worker import create_app

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 55933
DEFAULT_THREADS = 4
DEFAULT_CONFIG = 'conf/mtw-dist.ini'

appname = 'mtw-worker'
appdesc = 'MTW Worker 0.1.8'
appusage = 'Help:  ' + appname + ' -h \n'
appauthor = 'Filip Kriz'


def start():
    parser = argparse.ArgumentParser(description=appdesc, prog=appname, usage='%(prog)s [options]')
    parser.add_argument('--config', type=str, help='Config file path - default: ' + DEFAULT_CONFIG, default=DEFAULT_CONFIG)
    parser.add_argument('--debug', help='Run in debug mode - DO NOT use in production !', action='store_true')
    parser.add_argument('--host', type=str, help='Host - default: ' + DEFAULT_HOST, default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, help='Port number - default: ' + str(DEFAULT_PORT), default=DEFAULT_PORT)
    parser.add_argument('--relax', help='Run in relaxed mode - DO NOT use in production !', action='store_true')
    parser.add_argument('--threads', type=int, help='Number of threads - default: ' + str(DEFAULT_THREADS), default=DEFAULT_THREADS)

    args, unknown = parser.parse_known_args()

    if unknown:
        print('\nERROR : Uknown arguments : ', unknown)
        print('Try help : py ' + appname + '.py -h')
        return

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.ERROR)

    app = create_app(debug=args.debug, logger=logger, port=args.port,
                     config_path=args.config,
                     relax=args.relax)

    if not app:
        print('Server cannot be started - check the config / modify the args / check if the port is available')
        return

    if getattr(sys, 'frozen', False):
        app.static_folder = os.path.join(os.path.dirname(sys.executable), 'static')
        app.template_folder = os.path.join(os.path.dirname(sys.executable), 'templates')

    try:
        serve(app, host=args.host, port=args.port, threads=args.threads)

    except:  # noqa: E722
        print('Server cannot be started - check the config / modify the args / check if the port is available')


if __name__ == '__main__':
    start()
