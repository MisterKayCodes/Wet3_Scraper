import os
import sys
import asyncio
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.tl.types import ChatInviteAlready
import config

API_ID = config.API_ID
API_HASH = config.API_HASH
SESSION_STRING = config.SESSION_STRING

class TelegramService:
    def __init__(self):
        self.client = TelegramClient(
            StringSession(SESSION_STRING), 
            API_ID, 
            API_HASH,
            connection_retries=5,
            retry_delay=5,
            timeout=30
        )
        self.target_channel = None

    async def start(self):
        if not self.client.is_connected():
            await self.client.connect()
        if not await self.client.is_user_authorized():
            print("[!] Telegram Client not authorized. Please check SESSION_STRING.")
            return False
        print("[+] Telegram Client Connected.")
        return True

    async def resolve_channel(self, invite_link):
        """Resolves an invite link or channel username to a peer entity."""
        if not invite_link:
            return
        try:
            if "t.me/+" in invite_link or "t.me/joinchat/" in invite_link:
                # It's a private invite link
                hash_code = invite_link.split('/')[-1].replace('+', '')
                invite = await self.client(functions.messages.CheckChatInviteRequest(hash_code))
                
                if isinstance(invite, ChatInviteAlready):
                    print(f"[*] Already a member of: {invite.chat.title}", flush=True)
                    self.target_channel = invite.chat
                else:
                    print(f"[*] Resolving Invite for: {invite.title}", flush=True)
                    # Attempt to join
                    try:
                        await self.client(functions.messages.ImportChatInviteRequest(hash_code))
                    except Exception as e:
                        if "USER_ALREADY_PARTICIPANT" not in str(e):
                            raise e
                    self.target_channel = await self.client.get_entity(invite_link)
            else:
                # Public channel username or ID
                self.target_channel = await self.client.get_entity(invite_link)
            
            print(f"[+] Resolved Target: {self.target_channel.title} (ID: {self.target_channel.id})", flush=True)
        except Exception as e:
            print(f"[!] Could not resolve channel: {e}", flush=True)
            raise e

    async def upload_video(self, file_path, caption):
        """Uploads a video file with a caption."""
        if not self.target_channel:
            raise Exception("Target channel not resolved. Call resolve_channel first.")
            
        print(f"[*] Uploading to Telegram: {os.path.basename(file_path)}...", flush=True)
        try:
            await self.client.send_file(
                self.target_channel,
                file_path,
                caption=caption,
                parse_mode='html',
                progress_callback=self._progress_callback
            )
            return True
        except Exception as e:
            print(f"[!] Upload failed: {e}", flush=True)
            return False

    async def send_log(self, message):
        """Sends a text-based log message to the channel."""
        if not self.target_channel:
            return False
        try:
            await self.client.send_message(self.target_channel, f"<code>[LOG]</code> {message}", parse_mode='html')
            return True
        except Exception as e:
            print(f"[!] Log failed: {e}", flush=True)
            return False

    async def send_test_message(self, text, delay=15):
        """Sends a message and deletes it after a delay."""
        if not self.target_channel:
            return False
        try:
            msg = await self.client.send_message(self.target_channel, text, parse_mode='html')
            # Wait in background so we don't block the caller
            asyncio.create_task(self._delayed_delete(msg.id, delay))
            return True
        except Exception as e:
            print(f"[!] Test message failed: {e}")
            return False

    async def _delayed_delete(self, msg_id, delay):
        await asyncio.sleep(delay)
        try:
            await self.client.delete_messages(self.target_channel, [msg_id])
        except:
            pass

    def _progress_callback(self, current, total):
        percent = (current / total) * 100
        sys.stdout.write(f"\r    Uploading... {percent:.1f}% ({current}/{total} bytes)")
        sys.stdout.flush()


def upload_file_sync(file_path, caption, channel_link):
    """
    DEADLOCK-FREE standalone uploader.
    
    Runs in a Worker Thread with its OWN fresh asyncio event loop.
    Does NOT share any loop with Aiogram or Telethon's main client.
    Creates a fresh Telethon connection, uploads, and disconnects cleanly.
    """
    def _progress(current, total):
        percent = (current / total) * 100
        sys.stdout.write(f"\r    [UPLOAD] {percent:.1f}% ({current // 1024 // 1024}MB / {total // 1024 // 1024}MB)")
        sys.stdout.flush()

    async def _run():
        print(f"\n[*] 📡 Connecting fresh Telethon client for upload...", flush=True)
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH,
                                connection_retries=5, retry_delay=5)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("[!] Upload client not authorized!", flush=True)
            await client.disconnect()
            return False
        
        try:
            # Resolve the channel target
            if "t.me/+" in channel_link or "t.me/joinchat/" in channel_link:
                from telethon import functions
                from telethon.tl.types import ChatInviteAlready
                hash_code = channel_link.split('/')[-1].replace('+', '')
                invite = await client(functions.messages.CheckChatInviteRequest(hash_code))
                if isinstance(invite, ChatInviteAlready):
                    target = invite.chat
                else:
                    target = await client.get_entity(channel_link)
            else:
                target = await client.get_entity(channel_link)
            
            # --- EXTRACT THUMBNAIL ---
            thumb_path = file_path + ".jpg"
            try:
                import imageio_ffmpeg
                import subprocess
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                print(f"\n[*] 🖼️ Extracting video thumbnail...", flush=True)
                # Extract a frame at the 2-second mark
                subprocess.run(
                    [ffmpeg_exe, "-ss", "00:00:02", "-i", file_path, "-vframes", "1", "-q:v", "2", "-y", thumb_path],
                    capture_output=True, timeout=30
                )
            except Exception as e:
                print(f"[!] Could not extract thumbnail: {e}", flush=True)
                thumb_path = None
            
            if thumb_path and not os.path.exists(thumb_path):
                thumb_path = None

            # --- EXTRACT METADATA (To fix Zoomed-In Video Issue) ---
            import re
            width, height, duration = 0, 0, 0
            try:
                meta_res = subprocess.run([ffmpeg_exe, "-i", file_path], capture_output=True, text=True, timeout=15)
                out = meta_res.stderr
                # Parse Duration: 00:00:10.00
                dur_match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})", out)
                if dur_match:
                    duration = int(dur_match.group(1)) * 3600 + int(dur_match.group(2)) * 60 + int(dur_match.group(3))
                # Parse Video: h264, yuv420p, 1920x1080
                res_match = re.search(r"Video:.*?,.*?(\d{3,5})x(\d{3,5})", out)
                if res_match:
                    width = int(res_match.group(1))
                    height = int(res_match.group(2))
            except Exception as meta_err:
                print(f"[!] Warning: Could not extract metadata dimensions: {meta_err}")

            print(f"\n[*] 📤 Uploading {os.path.basename(file_path)} ({width}x{height}) to Telegram...", flush=True)
            from telethon.tl.types import DocumentAttributeVideo
            
            video_attr = DocumentAttributeVideo(
                duration=duration,
                w=width,
                h=height,
                supports_streaming=True
            )
            
            await client.send_file(
                target, 
                file_path, 
                caption=caption,
                parse_mode='html', 
                progress_callback=_progress,
                attributes=[video_attr],
                thumb=thumb_path
            )
            
            # Clean up thumbnail
            try:
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
            except: pass
            print(f"\n[+] ✅ Upload complete!", flush=True)
            return True
        except Exception as e:
            print(f"\n[!] Upload failed: {e}", flush=True)
            return False
        finally:
            await client.disconnect()

    # Spawn a COMPLETELY isolated daemon thread with zero event loop inheritance.
    # This is immune to all asyncio loop conflicts - the thread starts fresh.
    import threading
    result = [False]

    def _thread_run():
        # This thread has NO running loop, so asyncio.run() works perfectly here
        result[0] = asyncio.run(_run())

    t = threading.Thread(target=_thread_run, daemon=True)
    t.start()
    # Use a loop so Ctrl+C (KeyboardInterrupt) can interrupt the wait
    try:
        while t.is_alive():
            t.join(timeout=1)
    except KeyboardInterrupt:
        print("\n[!] Upload interrupted by user.", flush=True)
        raise  # Re-raise so the bot can shut down gracefully
    return result[0]
