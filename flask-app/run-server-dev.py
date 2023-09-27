# -*- coding: utf-8 -*-
DEFAULT_PORT = 5900
DEFAULT_CONFIG = 'conf/mtw.ini'

import sys
from application import create_app

def main():
    if len(sys.argv) == 2:
        config_path = sys.argv[1]
    else:
        config_path = DEFAULT_CONFIG

    debug = True
    threaded = True

    app = create_app(debug=debug, config_path=config_path, port=DEFAULT_PORT)
    app.run(port=DEFAULT_PORT, debug=debug, threaded=threaded)


if __name__ == "__main__":
    main()
