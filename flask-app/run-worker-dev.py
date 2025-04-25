# -*- coding: utf-8 -*-
import sys
from application.worker import create_app

DEFAULT_PORT = 5903
DEFAULT_CONFIG = "conf/mtw.ini"


def start():
    if len(sys.argv) == 2:
        config_path = sys.argv[1]
    else:
        config_path = DEFAULT_CONFIG

    app = create_app(debug=True, config_path=config_path, port=DEFAULT_PORT)
    app.run(port=DEFAULT_PORT, debug=True, threaded=True)


if __name__ == "__main__":
    start()
