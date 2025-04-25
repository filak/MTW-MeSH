# -*- coding: utf-8 -*-
"""
Flask Extensions
"""
from flask_caching import Cache

# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
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

"""
limiter = Limiter(key_func=get_remote_address,
                  headers_enabled=False,
                  in_memory_fallback_enabled=True,
                  default_limits=["60/minute"])
"""
