# -*- coding: utf-8 -*-
from telegram.ext import CommandHandler
from config.settings import Settings

async def status_cmd(update, context):
    await update.message.reply_text("Status OK")

class AdminCommandsHandler:
    def __init__(self, settings: Settings, db_manager, user_manager, scheduler=None):
        self.settings = settings
        self.db_manager = db_manager
        self.user_manager = user_manager
        self.scheduler = scheduler

    async def register_handlers(self, app, command_bus):
        app.add_handler(CommandHandler("status", status_cmd))
