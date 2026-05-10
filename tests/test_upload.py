"""
Test: Deadlock-Free Telegram Upload
====================================
Simulates the exact same environment as the bot:
- A running asyncio event loop (like aiogram)
- The upload running in a thread executor (like our scraper worker)

Run from project root: python tests/test_upload.py
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# Load the channel link the same way the real bot does:
# First try config (set via /set_channel command), then fall back to settings.json
def get_channel_link():
    if config.CHANNEL_LINK:
        return config.CHANNEL_LINK
    try:
        from utils.settings_manager import load_settings
        link = load_settings().get("target_channel", "")
        if link:
            print(f"[*] Loaded channel link from settings.json: {link}")
            return link
    except Exception as e:
        print(f"[!] Could not load settings.json: {e}")
    return ""

def test_upload_file_sync_standalone():
    """Test 1: upload_file_sync called directly (no running loop)."""
    print("\n" + "="*60)
    print("TEST 1: Direct call (no running loop)")
    print("="*60)
    from core.telegram_utils import upload_file_sync
    
    channel_link = get_channel_link()
    if not channel_link:
        print("[!] No channel link found in config or settings.json. Did you run /set_channel?")
        return False

    test_file = "tests/test_upload_dummy.txt"
    with open(test_file, "w") as f:
        f.write("Test upload from Wet3 Scraper bot - please ignore.")
    
    result = upload_file_sync(
        file_path=test_file,
        caption="🤖 <b>TEST UPLOAD</b>\n<i>Verifying deadlock-free uploader works.</i>",
        channel_link=channel_link
    )
    
    print(f"\n✅ Test 1 Result: {'PASSED' if result else 'FAILED'}")
    return result


async def test_upload_from_executor():
    """Test 2: upload_file_sync called from inside a running event loop via executor."""
    print("\n" + "="*60)
    print("TEST 2: Called from executor (simulates real bot environment)")
    print("="*60)
    from core.telegram_utils import upload_file_sync
    
    channel_link = get_channel_link()
    if not channel_link:
        print("[!] No channel link found. Skipping Test 2.")
        return False

    test_file = "tests/test_upload_dummy.txt"
    with open(test_file, "w") as f:
        f.write("Test upload from executor - simulating bot environment.")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        upload_file_sync,
        test_file,
        "🤖 <b>TEST UPLOAD (Executor)</b>\n<i>This simulates the real bot environment.</i>",
        channel_link
    )
    
    print(f"\n✅ Test 2 Result: {'PASSED' if result else 'FAILED'}")
    return result



if __name__ == "__main__":
    print("🧪 STARTING UPLOAD TESTS")
    print("Testing that upload works in both standalone and executor contexts...")

    # Test 1: Direct call
    t1 = test_upload_file_sync_standalone()

    # Test 2: From inside a running event loop (the real scenario)
    t2 = asyncio.run(test_upload_from_executor())

    print("\n" + "="*60)
    print(f"FINAL RESULTS:")
    print(f"  Test 1 (standalone):  {'✅ PASSED' if t1 else '❌ FAILED'}")
    print(f"  Test 2 (executor):    {'✅ PASSED' if t2 else '❌ FAILED'}")
    print("="*60)
    
    if t1 and t2:
        print("\n🎉 ALL TESTS PASSED. Safe to deploy.")
    else:
        print("\n💥 TESTS FAILED. Do not deploy.")
        sys.exit(1)
