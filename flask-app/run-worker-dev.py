# -*- coding: utf-8 -*-
DEFAULT_CONFIG = 'conf/mtw.ini'

import sys
from application.worker import create_app

def main():
    if len(sys.argv) == 2:
        config_path = sys.argv[1]
    else:
        config_path = DEFAULT_CONFIG

    debug = True
    threaded = True

    app = create_app(debug=debug, config_path=config_path)
    app.run(port=5903, debug=debug, threaded=threaded)


if __name__ == "__main__":
    main()
