# -*- coding: utf-8 -*-
#SERVER_HOSTNAME = 'localhost'
SERVER_PORT = 55930 #55931
SERVICE_NAME = 'MTWServer'
SERVICE_DISPLAY_NAME = 'MTW Server'
SERVICE_DESCRIPTION = 'MeSH Translation Workflow Service'

import win32timezone
import win32service
import win32serviceutil
import win32event
import win32api
import servicemanager

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
##from tornado.platform.asyncio import AnyThreadEventLoopPolicy
##import asyncio
import os, sys
from mtw.flask import app

service_stop_event = win32event.CreateEvent(None, 0, 0, None)

def run_server():
    if getattr(sys, 'frozen', False):
        app.static_folder = os.path.join(os.path.dirname(sys.executable), 'static')
        app.template_folder = os.path.join(os.path.dirname(sys.executable), 'templates')

    ##asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    ##asyncio.set_event_loop_policy(tornado.platform.asyncio.AnyThreadEventLoopPolicy())
    ##asyncio.set_event_loop(asyncio.new_event_loop())

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen( int( os.environ.get('MTW_SERVER_PORT', SERVER_PORT) ) )

    IOLoop.instance().start()

def stop_server():
    IOLoop.instance().stop()

class Service(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME + '-' + str( os.environ.get('MTW_SERVER_PORT', SERVER_PORT) )
    _svc_display_name_ = SERVICE_DISPLAY_NAME + ' - port:' + str( os.environ.get('MTW_SERVER_PORT', SERVER_PORT) )
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, *args, **kwargs):
        win32serviceutil.ServiceFramework.__init__(self, *args, **kwargs)

    def SvcDoRun(self):
        run_server()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcStop(self):
        stop_server()
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(service_stop_event)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(Service)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(Service)

