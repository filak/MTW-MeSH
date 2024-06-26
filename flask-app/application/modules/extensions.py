# -*- coding: utf-8 -*-
"""
Flask Extensions
"""
from flask_caching import Cache
from flask_paranoid import Paranoid
from flask_seasurf import SeaSurf
from flask_session import Session
# from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman  # noqa: F401

cache = Cache()

csrf = SeaSurf()

# db = SQLAlchemy()

paranoid = Paranoid()

sess = Session()
