import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from loguru import logger

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

# --- PHASE 1: LOGGING FOUNDATION ---
# Ensure logs directory exists and set up file logging
Path("logs").mkdir(exist_ok=True)
logger.add("logs/bot.log", rotation="10 MB", retention="7 days", level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient
from telethon.sessions import StringSession

# Ensure root is in path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import config
import ui
from utils.settings_manager import load_settings, save_settings
from services.orchestrator import ScrapeOrchestrator
from core.telegram_utils import TelegramService

# --- CONFIG & STATE ---
# (Moved to utils/settings_manager.py)

# --- INITIALIZATION ---
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
orchestrator = ScrapeOrchestrator()
# Telethon Worker (for large uploads)
telethon_worker = TelegramService()

import handlers

# --- AIOGRAM HANDLERS ---
# All commands have been moved to handlers.py (Phase 2 & 3)

# Inject dependencies into the dispatcher
dp["orchestrator"] = orchestrator
dp["telethon_worker"] = telethon_worker

# Include the external router
dp.include_router(handlers.get_router())

async def main():
    logger.info("Initializing Hybrid Bot...")
    
    # Set bot commands in the menu
    commands = [
        types.BotCommand(command="start", description="Show welcome message"),
        types.BotCommand(command="status", description="Check bot health"),
        types.BotCommand(command="logs", description="View recent terminal logs"),
        types.BotCommand(command="set_channel", description="Set destination channel"),
        types.BotCommand(command="test_target", description="Test connection to channel"),
        types.BotCommand(command="scrape", description="Start scraping a URL"),
    ]
    await bot.set_my_commands(commands)
    
    # 1. Start Telethon Worker
    await telethon_worker.start()
    settings = load_settings()
    
    target = settings.get("target_channel")
    if target:
        try:
            await telethon_worker.resolve_channel(target)
        except Exception as e:
            logger.warning(f"Could not resolve initial channel '{target}': {e}")
    else:
        logger.warning("No target channel set. Use /set_channel in Telegram to configure.")
    
    # 2. Start Aiogram Polling
    logger.info("Bot is Online (Aiogram UI + Telethon Worker)")
    try:
        # Drop pending updates so it doesn't process old ignored clicks
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Initiating graceful shutdown...")
        if telethon_worker.client.is_connected():
            await telethon_worker.client.disconnect()
        await bot.session.close()
        logger.info("Shutdown complete. Your code is safe!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
