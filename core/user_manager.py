# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from config.settings import Settings

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

class SessionState(str, Enum):
    IDLE = "idle"

@dataclass
class Session:
    user_id: int
    chat_id: int
    state: SessionState = SessionState.IDLE
    data: Dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=now_utc)
    is_authenticated: bool = False

class UserManager:
    def __init__(self, db_manager, settings: Settings):
        self.db_manager = db_manager
        self.settings = settings
        self._sessions: Dict[str, Session] = {}
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        return

    async def get_session(self, user_id: int, chat_id: int) -> Session:
        key = f"{user_id}:{chat_id}"
        if key not in self._sessions:
            self._sessions[key] = Session(user_id=user_id, chat_id=chat_id)
        return self._sessions[key]

    async def update_session(self, session: Session):
        key = f"{session.user_id}:{session.chat_id}"
        self._sessions[key] = session

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.settings.ADMIN_USERS
