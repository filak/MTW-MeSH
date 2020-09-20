# -*- coding: utf-8 -*-
import os, sys
from mtw.flask import app

if getattr(sys, 'frozen', False):
    app.static_folder = os.path.join(os.path.dirname(sys.executable), 'static')
    app.template_folder = os.path.join(os.path.dirname(sys.executable), 'templates')

if __name__ == "__main__":
    app.run(port=5900,debug=True,threaded=True)
