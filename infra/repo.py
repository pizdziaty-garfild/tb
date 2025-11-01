# -*- coding: utf-8 -*-
"""
Simple in-memory repository with JSON persistence for dev (sync path)
Switch to SQLAlchemy later.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

from domain.models import BotSettings, Group

STORE = Path("data/repo_store.json")


def _now():
    return datetime.now(timezone.utc).isoformat()


class Repo:
    def __init__(self):
        self._data = {"settings": {}, "groups": {}}
        self._load()

    def _load(self):
        if STORE.exists():
            try:
                self._data = json.loads(STORE.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save(self):
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Settings
    def get_settings(self) -> BotSettings:
        s = self._data.get("settings") or {}
        return BotSettings(
            info_name=s.get("info_name"),
            info_channel=s.get("info_channel"),
            info_group=s.get("info_group"),
            welcome_message=s.get("welcome_message"),
            contact=s.get("contact"),
            global_interval_min=s.get("global_interval_min", 5),
        )

    def set_settings(self, s: BotSettings):
        self._data["settings"] = {
            "info_name": s.info_name,
            "info_channel": s.info_channel,
            "info_group": s.info_group,
            "welcome_message": s.welcome_message,
            "contact": s.contact,
            "global_interval_min": s.global_interval_min,
            "updated_at": _now(),
        }
        self._save()

    # Groups
    def list_groups(self) -> List[Group]:
        out = []
        for gid, g in self._data.get("groups", {}).items():
            out.append(Group(
                chat_id=gid,
                username=g.get("username"),
                name=g.get("name"),
                custom_interval_min=g.get("custom_interval_min"),
                excluded_from_global=g.get("excluded_from_global", False),
            ))
        return out

    def add_groups(self, items: List[str]) -> int:
        count = 0
        self._data.setdefault("groups", {})
        for it in items:
            gid = it.strip()
            if not gid:
                continue
            # simple dedup
            if gid in self._data["groups"]:
                continue
            self._data["groups"][gid] = {
                "username": gid[1:] if gid.startswith("@") else None,
                "name": None,
                "custom_interval_min": None,
                "excluded_from_global": False,
                "created_at": _now(),
                "updated_at": _now(),
            }
            count += 1
        if count:
            self._save()
        return count

    def del_groups(self, items: List[str]) -> int:
        count = 0
        if "groups" not in self._data:
            return 0
        for it in items:
            if it in self._data["groups"]:
                del self._data["groups"][it]
                count += 1
        if count:
            self._save()
        return count

    def set_excluded(self, items: List[str], excluded: bool) -> int:
        count = 0
        for it in items:
            g = self._data.get("groups", {}).get(it)
            if not g:
                continue
            g["excluded_from_global"] = excluded
            g["updated_at"] = _now()
            count += 1
        if count:
            self._save()
        return count

    def set_group_interval(self, gid: str, minutes: int) -> bool:
        g = self._data.get("groups", {}).get(gid)
        if not g:
            return False
        g["custom_interval_min"] = minutes
        g["updated_at"] = _now()
        self._save()
        return True
