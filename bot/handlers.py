from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import os
import html
import platform
import psutil

import ui
import config
from utils.settings_manager import load_settings, save_settings

# Create the primary router for bot commands
router = Router()

def get_router():
    """
    Returns the configured router. 
    Dependencies like orchestrator and telethon_worker will be injected by Aiogram.
    """
    return router

# --- PHASE 2: SIMPLE COMMANDS ---

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(ui.get_start_message())

@router.message(Command("set_channel"))
async def cmd_set_channel(message: types.Message, telethon_worker):
    args = message.text.split(" ")
    if len(args) < 2:
        await message.answer("⚠️ Usage: `/set_channel [Invite Link]`")
        return
    
    new_link = args[1].strip().replace('"', '').replace("'", "")
    settings = load_settings()
    settings["target_channel"] = new_link
    save_settings(settings)
    
    config.CHANNEL_LINK = new_link
    try:
        await telethon_worker.resolve_channel(new_link)
        await message.answer(f"✅ Target channel updated to: `{new_link}`")
    except Exception as e:
        await message.answer(f"❌ Failed to resolve channel: {e}")

@router.message(Command("test_target"))
async def cmd_test_target(message: types.Message, telethon_worker):
    settings = load_settings()
    target = settings.get("target_channel")
    
    if not target:
        await message.answer("⚠️ No target channel set. Use `/set_channel` first.")
        return
        
    status_msg = await message.answer(f"📡 Testing connection to <code>{target}</code>...")
    
    try:
        await telethon_worker.send_test_message(f"🔔 <b>Bot Connection Verified!</b>\nAll systems are go for media relay.", delay=15)
        await status_msg.edit_text(ui.get_test_target_message(target, True))
    except Exception as e:
        await status_msg.edit_text(ui.get_test_target_message(target, False, str(e)))

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    settings = load_settings()
    target = settings.get("target_channel", "Not set")
    
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    
    await message.answer(ui.get_status_message(platform.system(), cpu_usage, ram_usage, target))

@router.message(Command("logs"))
async def cmd_logs(message: types.Message):
    """Sends the last 20 lines of the bot log."""
    log_path = "logs/bot.log"
    if not os.path.exists(log_path):
        await message.answer("⚠️ No log file found yet.")
        return
        
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            last_lines = lines[-20:] # Get last 20 lines
            log_text = "".join(last_lines)
            
        if not log_text:
            await message.answer("📭 Log file is currently empty.")
        else:
            # Escape HTML to prevent "can't parse entities" errors
            safe_log = html.escape(log_text)
            await message.answer(f"📝 <b>Recent Logs:</b>\n<pre>{safe_log}</pre>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Failed to read logs: {e}")

# --- PHASE 3: SCRAPING ENGINE ---

@router.message(Command("scrape"))
async def cmd_scrape(message: types.Message, orchestrator, telethon_worker, bot: Bot):
    args = message.text.split(" ")
    if len(args) < 2:
        await message.answer("⚠️ Usage: `/scrape [URL]`")
        return

    url = args[1]
    profile_name = url.strip('/').split('/')[-1]
    
    status_msg = await message.answer(ui.get_analysis_message(profile_name))
    
    # Run scrape in executor (sync logic)
    loop = asyncio.get_event_loop()
    
    def status_callback(text):
        asyncio.run_coroutine_threadsafe(
            bot.edit_message_text(text, chat_id=status_msg.chat.id, message_id=status_msg.message_id),
            loop
        )

    result = await loop.run_in_executor(None, orchestrator.run_full_pipeline, url, profile_name, "none", True, None, status_callback, telethon_worker)
    
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

@router.message(Command("set_session"))
async def cmd_set_session(message: types.Message):
    """
    Updates the session.json file on the VPS remotely.
    The user can paste the JSON content after the command.
    """
    import json
    # Strip command and get the JSON string
    json_text = message.text.replace("/set_session", "").strip()
    
    if not json_text:
        await message.answer("âš ï¸  <b>Usage:</b>\n<code>/set_session [PASTE_JSON_HERE]</code>\n\n<i>Get the JSON from your local capture_session.py script.</i>")
        return

    try:
        # Validate JSON structure
        data = json.loads(json_text)
        if "cookies" not in data or "user_agent" not in data:
            raise ValueError("JSON must contain 'cookies' and 'user_agent' keys.")
            
        # Save to the data directory
        session_path = os.path.join("data", "session.json")
        os.makedirs("data", exist_ok=True)
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        await message.answer("âœ… <b>Session Updated!</b>\nThe scraper will pick up the new cookies automatically for the next batch.")
    except Exception as e:
        await message.answer(f"â Œ <b>Invalid Session Data:</b>\n<code>{str(e)}</code>")

@router.callback_query(F.data.startswith("dl:"))
async def handle_download(callback: types.CallbackQuery, orchestrator, telethon_worker, bot: Bot):
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
    
    last_update_time = [0] # Use a list so we can modify it inside the nested function
    
    def progress_callback(current, total):
        import time
        now = time.time()
        
        # THROTTLE: Only update Telegram once every 2 seconds, OR when 100% finished
        if now - last_update_time[0] > 2.0 or current == total:
            last_update_time[0] = now
            percentage = (current / total) * 100
            text = ui.get_download_progress(profile_name, mode, percentage, current, total)
            # Use bot.edit_message_text for live updates safely on the main loop
            asyncio.run_coroutine_threadsafe(
                bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id),
                asyncio.get_event_loop()
            )

    def status_callback(text):
        # We only update status if it's not a progress bar update (to avoid overlapping)
        if "Processing" in text or "Queueing" in text:
            asyncio.run_coroutine_threadsafe(
                bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id),
                asyncio.get_event_loop()
            )

    # Run orchestrated pipeline
    loop = asyncio.get_event_loop()
    url = f"https://wet3.click/user/{profile_name}"
    await loop.run_in_executor(None, orchestrator.run_full_pipeline, url, profile_name, mode, True, progress_callback, status_callback, telethon_worker)
    
    await callback.message.answer(ui.get_finished_message(profile_name))
