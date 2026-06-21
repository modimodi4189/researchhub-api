"""
Shared rate limiter instance.

Defined here to avoid circular imports:
  main.py imports routers -> routers need the limiter -> limiter can't import main.

app/main.py and all routers import from this module.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
