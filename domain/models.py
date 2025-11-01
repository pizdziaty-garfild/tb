# -*- coding: utf-8 -*-
"""
Domain models for settings and groups.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


@dataclass
class BotSettings:
    id: int = 1
    info_name: Optional[str] = None       # @nazwa
    info_channel: Optional[str] = None    # @kanal
    info_group: Optional[str] = None      # @grupa
    welcome_message: Optional[str] = None
    contact: Optional[str] = None         # @admin
    global_interval_min: int = 5
    updated_at: datetime = field(default_factory=now_utc)


@dataclass
class Group:
    chat_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    custom_interval_min: Optional[int] = None
    excluded_from_global: bool = False
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
