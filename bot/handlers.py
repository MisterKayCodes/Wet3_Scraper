from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
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

# --- PHASE 3: SCRAPING ENGINE ---

@router.message(Command("scrape"))
async def cmd_scrape(message: types.Message, orchestrator, telethon_worker):
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
    
    def progress_callback(current, total):
        percentage = (current / total) * 100
        text = ui.get_download_progress(profile_name, mode, percentage, current, total)
        # Use bot.edit_message_text for live updates safely on the main loop
        asyncio.run_coroutine_threadsafe(
            bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id),
            asyncio.get_event_loop()
        )

    # Run orchestrated pipeline
    loop = asyncio.get_event_loop()
    url = f"https://wet3.click/user/{profile_name}"
    await loop.run_in_executor(None, orchestrator.run_full_pipeline, url, profile_name, mode, True, progress_callback, telethon_worker)
    
    await callback.message.answer(ui.get_finished_message(profile_name))
