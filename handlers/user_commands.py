# -*- coding: utf-8 -*-
from telegram.ext import ApplicationBuilder, CommandHandler
from config.settings import Settings

async def start(update, context):
    await update.message.reply_text("Bot działa. /info po więcej")

async def info(update, context):
    await update.message.reply_text("Info: wersja 1.0.0")

class UserCommandsHandler:
    def __init__(self, settings: Settings, user_manager):
        self.settings = settings
        self.user_manager = user_manager

    async def register_handlers(self, app, command_bus):
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("info", info))
