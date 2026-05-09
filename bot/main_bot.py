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
@dp.message(Command("scrape"))
async def cmd_scrape(message: types.Message):
    args = message.text.split(" ")
    if len(args) < 2:
        await message.answer("⚠️ Usage: `/scrape [URL]`")
        return

    url = args[1]
    profile_name = url.strip('/').split('/')[-1]
    
    status_msg = await message.answer(ui.get_analysis_message(profile_name))
    
    # Run scrape in executor (sync logic)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, orchestrator.run_full_pipeline, url, profile_name, "none", True, None, telethon_worker)
    
    if result.get("status") == "success":
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Download 1", callback_data=f"dl:{profile_name}:1"))
        builder.row(types.InlineKeyboardButton(text="Download 10", callback_data=f"dl:{profile_name}:10"))
        builder.row(types.InlineKeyboardButton(text="Download ALL", callback_data=f"dl:{profile_name}:all"))
        
        await status_msg.edit_text(
            f"✅ **Analysis Complete: {profile_name}**\nFound items. Select mode:",
            reply_markup=builder.as_markup()
        )
    else:
        await status_msg.edit_text(f"❌ **Error:** {result.get('message')}")

@dp.callback_query(F.data.startswith("dl:"))
async def handle_download(callback: types.CallbackQuery):
    _, profile_name, mode = callback.data.split(":")
    
    settings = load_settings()
    target = settings.get("target_channel")
    
    # --- PRE-FLIGHT SAFETY CHECK ---
    if not target:
        await callback.answer("❌ No target channel set! Use /set_channel first.", show_alert=True)
        return
        
    try:
        await telethon_worker.resolve_channel(target)
    except Exception as e:
        await callback.message.answer(f"⚠️ <b>Permissions Error:</b> Cannot access channel <code>{target}</code>.\nError: {e}\n\n<i>Please fix permissions and try again.</i>")
        return
    # -------------------------------
    
    await callback.message.edit_text(ui.get_download_progress(profile_name, mode, 0, 0, 100)) # Init bar
    
    def progress_callback(current, total):
        percentage = (current / total) * 100
        text = ui.get_download_progress(profile_name, mode, percentage, current, total)
        # Use bot.edit_message_text for live updates
        asyncio.run_coroutine_threadsafe(
            bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id),
            asyncio.get_event_loop()
        )

    # Run orchestrated pipeline
    loop = asyncio.get_event_loop()
    url = f"https://wet3.click/user/{profile_name}"
    await loop.run_in_executor(None, orchestrator.run_full_pipeline, url, profile_name, mode, True, progress_callback, telethon_worker)
    
    await callback.message.answer(ui.get_finished_message(profile_name))

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
