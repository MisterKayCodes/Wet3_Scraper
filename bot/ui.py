"""
UI Templates for the Wet3 Hybrid Assistant.
Uses HTML formatting for a premium look.
"""

def get_start_message():
    return (
        "✨ <b>WET3 HYBRID ASSISTANT</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Your professional media acquisition engine is online.\n\n"
        "<b>Available Commands:</b>\n"
        "🔍 <code>/scrape [URL]</code> — Analyze a profile\n"
        "📍 <code>/set_channel [Link]</code> — Change destination\n"
        "📡 <code>/test_target</code> — Verify permissions\n"
        "📊 <code>/status</code> — System health report\n\n"
        "<i>Send a Wet3 link to begin.</i>"
    )

def get_status_message(os_name, cpu, ram, channel):
    return (
        "📊 <b>SYSTEM HEALTH REPORT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🖥️ <b>Platform:</b> <code>{os_name}</code>\n"
        f"🧠 <b>CPU Load:</b> <code>{cpu}%</code>\n"
        f"📟 <b>RAM Usage:</b> <code>{ram}%</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Target:</b> <code>{channel}</code>\n"
        "✅ <b>Status:</b> <code>Operational</code>"
    )

def get_analysis_message(profile_name):
    return (
        f"🔍 <b>ANALYZING PROFILE</b>\n"
        f"👤 <b>User:</b> <code>{profile_name}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚡ Bypassing ad-walls and security verification...\n"
        "🕒 This may take a few seconds."
    )

def get_download_progress(profile_name, mode, percentage, current, total):
    filled = int(percentage // 10)
    bar = "█" * filled + "░" * (10 - filled)
    return (
        f"📥 <b>DOWNLOADING CONTENT</b>\n"
        f"👤 <b>User:</b> <code>{profile_name}</code>\n"
        f"🛠️ <b>Mode:</b> <code>{mode.upper()}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Progress: [<code>{bar}</code>] <b>{percentage:.1f}%</b>\n"
        f"📦 Segments: <code>{current}</code> / <code>{total}</code>"
    )

def get_test_target_message(channel, success, error=None):
    status = "✅ <b>VERIFIED</b>" if success else "❌ <b>FAILED</b>"
    details = f"Details: <code>{error}</code>" if error else "The bot has permission to post to this channel."
    return (
        f"📍 <b>CHANNEL VERIFICATION</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Target: <code>{channel}</code>\n"
        f"Status: {status}\n\n"
        f"{details}"
    )

def get_finished_message(profile_name):
    return (
        f"✅ <b>TASK COMPLETED</b>\n"
        f"👤 <b>User:</b> <code>{profile_name}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "All media has been successfully processed and delivered to your channel."
    )
