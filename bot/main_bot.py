import os
import sys
import asyncio
import json
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
    print("[*] Initializing Hybrid Bot...")
    
    # 1. Start Telethon Worker
    await telethon_worker.start()
    settings = load_settings()
    
    target = settings.get("target_channel")
    if target:
        try:
            await telethon_worker.resolve_channel(target)
        except Exception as e:
            print(f"[!] Warning: Could not resolve initial channel '{target}': {e}")
    else:
        print("[!] No target channel set. Use /set_channel in Telegram to configure.")
    
    # 2. Start Aiogram Polling
    print("[+] Bot is Online (Aiogram UI + Telethon Worker)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
