# -*- coding: utf-8 -*-
from enum import Enum
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

class Role(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"

def require_role(min_role: Role):
    def deco(handler):
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            return await handler(update, context, *args, **kwargs)
        return wrapper
    return deco
