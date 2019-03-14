# -*- coding: utf-8 -*-
SERVER_PORT = 5903

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import os, sys
from mtw.worker import app

def run_server():
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(SERVER_PORT)
    IOLoop.instance().start()

def stop_server():
    IOLoop.instance().stop()

if __name__ == '__main__':
    try:
        print('Starting Tornado - port :  ', SERVER_PORT)
        run_server()
    except KeyboardInterrupt:
        print('Stopping Tornado')
        stop_server()




