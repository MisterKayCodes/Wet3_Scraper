from aiogram import Router, F, types
from aiogram.filters import Command
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
