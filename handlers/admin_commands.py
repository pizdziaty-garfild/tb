# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Admin Commands - Panel sterowania (/pusher alias) zgodnie z 2.2.1 i 2.2.3
- Inline menu: Set Info, Set Kontakt, Time, Ex-Time, Groups
- FSM + walidacja + batch operations
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config.settings import Settings
from core.user_manager import UserManager, SessionState

log = logging.getLogger(__name__)

# Callback data keys
class AdminAction(str, Enum):
    ROOT = "adm:root"
    SET_INFO = "adm:set_info"
    SET_CONTACT = "adm:set_contact"
    TIME = "adm:time"
    EX_TIME = "adm:ex_time"
    GROUPS = "adm:groups"

    # Submenus
    GROUPS_ADD = "adm:groups:add"
    GROUPS_DEL = "adm:groups:del"
    GROUPS_LIST = "adm:groups:list"

    EX_SET_GROUPS = "adm:ex:set_groups"
    EX_DEL_GROUPS = "adm:ex:del_groups"
    EX_SET_TIME = "adm:ex:set_time"


@dataclass
class AdminContext:
    awaiting: Optional[str] = None  # which input we wait for


class AdminCommandsHandler:
    def __init__(self, settings: Settings, db_manager, user_manager: UserManager, scheduler=None):
        self.settings = settings
        self.db = db_manager
        self.users = user_manager
        self.scheduler = scheduler

    async def register_handlers(self, app, command_bus):
        # /pusher alias
        app.add_handler(CommandHandler(self.settings.ADMIN_COMMAND, self._admin_root_cmd))
        # Callback buttons
        app.add_handler(CallbackQueryHandler(self._on_callback, pattern=r"^adm:"))
        # Text input for flows
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text_input))

    # ===== Root panel =====
    async def _admin_root_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in self.settings.ADMIN_USERS and uid != self.settings.OWNER_ID:
            await update.message.reply_text("⛔ Brak uprawnień")
            return
        await update.message.reply_text("Panel admina:", reply_markup=self._root_keyboard())

    def _root_keyboard(self) -> InlineKeyboardMarkup:
        kb = [
            [InlineKeyboardButton("📝 Set Info", callback_data=AdminAction.SET_INFO)],
            [InlineKeyboardButton("👤 Set Kontakt", callback_data=AdminAction.SET_CONTACT)],
            [InlineKeyboardButton("⏰ Time", callback_data=AdminAction.TIME)],
            [InlineKeyboardButton("⚙️ Ex-Time", callback_data=AdminAction.EX_TIME)],
            [InlineKeyboardButton("📋 Groups", callback_data=AdminAction.GROUPS)],
        ]
        return InlineKeyboardMarkup(kb)

    # ===== Callback router =====
    async def _on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        data = q.data
        if data == AdminAction.SET_INFO:
            await q.edit_message_text("Wyślij w jednej linii po przecinku: @nazwa,@kanal,@grupa,wiadomosc_powitalna\nPrzykład: @Sklep,@SklepKanal,@SklepGrupa,Witaj w naszym sklepie! ")
            self._set_admin_context(context, awaiting="set_info")
        elif data == AdminAction.SET_CONTACT:
            await q.edit_message_text("Wyślij nazwę kontaktu admina (np. @TwojNick)")
            self._set_admin_context(context, awaiting="set_contact")
        elif data == AdminAction.TIME:
            await q.edit_message_text("Wyślij globalny interwał (minuty), np. 5")
            self._set_admin_context(context, awaiting="set_time_global")
        elif data == AdminAction.EX_TIME:
            await q.edit_message_text(
                "Ex-Time:\n- Set Groups (wykluczenia)\n- Del Groups\n- Set Time (per grupa)\nWybierz:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Set Groups", callback_data=AdminAction.EX_SET_GROUPS)],
                    [InlineKeyboardButton("Del Groups", callback_data=AdminAction.EX_DEL_GROUPS)],
                    [InlineKeyboardButton("Set Time", callback_data=AdminAction.EX_SET_TIME)],
                    [InlineKeyboardButton("⬅️ Back", callback_data=AdminAction.ROOT)],
                ])
            )
            self._set_admin_context(context, awaiting=None)
        elif data == AdminAction.GROUPS:
            await q.edit_message_text(
                "Groups:\n- Add Groups\n- Del Groups\n- List",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Groups", callback_data=AdminAction.GROUPS_ADD)],
                    [InlineKeyboardButton("Del Groups", callback_data=AdminAction.GROUPS_DEL)],
                    [InlineKeyboardButton("List", callback_data=AdminAction.GROUPS_LIST)],
                    [InlineKeyboardButton("⬅️ Back", callback_data=AdminAction.ROOT)],
                ])
            )
            self._set_admin_context(context, awaiting=None)
        elif data == AdminAction.ROOT:
            await q.edit_message_text("Panel admina:", reply_markup=self._root_keyboard())
            self._set_admin_context(context, awaiting=None)
        elif data == AdminAction.EX_SET_GROUPS:
            await q.edit_message_text("Wklej listę group_id (każde w nowej linii) do wykluczenia z globalnego czasu:")
            self._set_admin_context(context, awaiting="ex_set_groups")
        elif data == AdminAction.EX_DEL_GROUPS:
            await q.edit_message_text("Wklej listę group_id do usunięcia z wykluczeń:")
            self._set_admin_context(context, awaiting="ex_del_groups")
        elif data == AdminAction.EX_SET_TIME:
            await q.edit_message_text("Podaj: group_id,minuty (np. -100123456789,3)")
            self._set_admin_context(context, awaiting="ex_set_time")
        elif data == AdminAction.GROUPS_ADD:
            await q.edit_message_text("Wklej listę group_id lub @username (po jednej pozycji w linii):")
            self._set_admin_context(context, awaiting="groups_add")
        elif data == AdminAction.GROUPS_DEL:
            await q.edit_message_text("Wklej listę group_id do usunięcia:")
            self._set_admin_context(context, awaiting="groups_del")
        elif data == AdminAction.GROUPS_LIST:
            # TODO: wyświetlić listę z paginacją (stub)
            await q.edit_message_text("Lista grup (stub) – do wdrożenia paginacja.")
            self._set_admin_context(context, awaiting=None)

    # ===== Text inputs =====
    async def _on_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.message:
            return
        uid = update.effective_user.id
        if uid not in self.settings.ADMIN_USERS and uid != self.settings.OWNER_ID:
            return
        adm_ctx = self._get_admin_context(context)
        text = update.message.text.strip()

        if adm_ctx.awaiting == "set_info":
            # TODO: zapisz do DB (info: nazwa, kanal, grupa, powitanie)
            await update.message.reply_text("Zapisano dane info (stub)")
            adm_ctx.awaiting = None
        elif adm_ctx.awaiting == "set_contact":
            # TODO: zapisz kontakt admina do DB
            await update.message.reply_text("Zapisano kontakt admina (stub)")
            adm_ctx.awaiting = None
        elif adm_ctx.awaiting == "set_time_global":
            try:
                minutes = int(text)
                if minutes < 1 or minutes > 1440:
                    raise ValueError
                # TODO: zapisz globalny interwał do DB + scheduler update
                await update.message.reply_text(f"Ustawiono globalny interwał: {minutes} min (stub)")
            except Exception:
                await update.message.reply_text("Nieprawidłowa wartość. Podaj liczbę minut 1–1440.")
            adm_ctx.awaiting = None
        elif adm_ctx.awaiting == "ex_set_groups":
            groups = [line.strip() for line in text.splitlines() if line.strip()]
            # TODO: walidacja + zapis wykluczeń do DB
            await update.message.reply_text(f"Dodano do wykluczeń: {len(groups)} (stub)")
            adm_ctx.awaiting = None
        elif adm_ctx.awaiting == "ex_del_groups":
            groups = [line.strip() for line in text.splitlines() if line.strip()]
            # TODO: usunięcie z wykluczeń
            await update.message.reply_text(f"Usunięto z wykluczeń: {len(groups)} (stub)")
            adm_ctx.awaiting = None
        elif adm_ctx.awaiting == "ex_set_time":
            try:
                gid, mins = text.split(",", 1)
                gid = gid.strip()
                mins = int(mins.strip())
                # TODO: zapis per-group interval
                await update.message.reply_text(f"Ustawiono {mins} min dla {gid} (stub)")
            except Exception:
                await update.message.reply_text("Format: group_id,minuty (np. -100123456789,3)")
            adm_ctx.awaiting = None
        elif adm_ctx.awaiting == "groups_add":
            items = [line.strip() for line in text.splitlines() if line.strip()]
            # TODO: walidacja, deduplikacja, zapis listy grup
            await update.message.reply_text(f"Dodano grup: {len(items)} (stub)")
            adm_ctx.awaiting = None
        elif adm_ctx.awaiting == "groups_del":
            items = [line.strip() for line in text.splitlines() if line.strip()]
            # TODO: usunięcie grup
            await update.message.reply_text(f"Usunięto grup: {len(items)} (stub)")
            adm_ctx.awaiting = None

    # ===== Helpers =====
    def _get_admin_context(self, context: ContextTypes.DEFAULT_TYPE) -> AdminContext:
        ctx = context.bot_data.get("admin_ctx")
        if not ctx:
            ctx = AdminContext()
            context.bot_data["admin_ctx"] = ctx
        return ctx

    def _set_admin_context(self, context: ContextTypes.DEFAULT_TYPE, *, awaiting: Optional[str]):
        ctx = self._get_admin_context(context)
        ctx.awaiting = awaiting
