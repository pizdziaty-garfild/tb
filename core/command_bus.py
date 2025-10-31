# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from core.user_manager import UserManager

class Priority(int, Enum):
    CRITICAL = 0
    HIGH = 10
    NORMAL = 20
    LOW = 30

@dataclass
class CommandHandler:
    name: str
    handler: Callable
    filter_func: Optional[Callable] = None
    priority: Priority = Priority.NORMAL
    requires_auth: bool = False
    requires_admin: bool = False
    states: Optional[List[str]] = None

class CommandBus:
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager
        self.logger = logging.getLogger(__name__)
        self.handlers: List[CommandHandler] = []

    def register_handler(self, name: str, handler: Callable, *,
                         filter_func: Optional[Callable] = None,
                         priority: Priority = Priority.NORMAL,
                         requires_auth: bool = False,
                         requires_admin: bool = False,
                         states: Optional[List[str]] = None):
        self.handlers.append(CommandHandler(name, handler, filter_func, priority, requires_auth, requires_admin, states))
        self.handlers.sort(key=lambda h: h.priority.value)

    async def dispatch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        return False

    def create_message_handler(self) -> MessageHandler:
        return MessageHandler(filters.ALL, self.dispatch)
