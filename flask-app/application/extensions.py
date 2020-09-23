# -*- coding: utf-8 -*-
"""
Flask Extensions
"""
#from flask_babel import Babel, gettext
from flask_caching import Cache
from flask_paranoid import Paranoid
from flask_seasurf import SeaSurf
from application.flask_session import Session
#from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman


#babel = Babel()

cache = Cache()

csrf = SeaSurf()

#db = SQLAlchemy()

paranoid = Paranoid()

sess = Session()

