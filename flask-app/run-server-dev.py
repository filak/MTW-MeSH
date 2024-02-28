# -*- coding: utf-8 -*-
DEFAULT_PORT = 5900
DEFAULT_CONFIG = 'conf/mtw.ini'

import sys
from application.main import create_app

def start():
    if len(sys.argv) == 2:
        config_path = sys.argv[1]
    else:
        config_path = DEFAULT_CONFIG

    app = create_app(debug=True, config_path=config_path, port=DEFAULT_PORT)
    app.run(port=DEFAULT_PORT, debug=True, threaded=False)


if __name__ == "__main__":
    start()

