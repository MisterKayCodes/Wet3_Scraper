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
    DEADLOCK-FREE standalone uploader with FloodWait protection.
    """
    from telethon.errors import FloodWaitError
    
    def _progress(current, total):
        percent = (current / total) * 100
        sys.stdout.write(f"\r    [UPLOAD] {percent:.1f}% ({current // 1024 // 1024}MB / {total // 1024 // 1024}MB)")
        sys.stdout.flush()

    async def _run():
        max_retries = 3
        for attempt in range(max_retries):
            print(f"\n[*] 📡 Connecting Telethon client (Attempt {attempt+1}/{max_retries})...", flush=True)
            client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH,
                                    connection_retries=5, retry_delay=5)
            await client.connect()
            
            if not await client.is_user_authorized():
                print("[!] Upload client not authorized!", flush=True)
                await client.disconnect()
                return False
            
            try:
                # Resolve target (Smart Caching: Use ID if provided to avoid invite check spam)
                target = await client.get_entity(channel_link)
                
                # --- MEDIA HANDLING ---
                is_image = file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
                thumb_path = None
                attributes = []
                
                if not is_image:
                    # Video-specific metadata
                    thumb_path = file_path + ".jpg"
                    try:
                        import imageio_ffmpeg
                        import subprocess
                        import shutil
                        import re
                        ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
                        
                        # Extract Meta
                        meta_res = subprocess.run([ffmpeg_exe, "-i", file_path], capture_output=True, text=True, timeout=15)
                        out = meta_res.stderr
                        width, height, duration = 1280, 720, 0
                        dur_match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})", out)
                        if dur_match: duration = int(dur_match.group(1)) * 3600 + int(dur_match.group(2)) * 60 + int(dur_match.group(3))
                        res_match = re.search(r"(\d{3,5})x(\d{3,5})", out)
                        if res_match:
                            width, height = int(res_match.group(1)), int(res_match.group(2))
                        
                        # Extract Thumb
                        if not os.path.exists(thumb_path):
                            subprocess.run([ffmpeg_exe, "-ss", "00:00:02", "-i", file_path, "-vframes", "1", "-y", thumb_path], capture_output=True, timeout=20)
                        
                        from telethon.tl.types import DocumentAttributeVideo
                        attributes.append(DocumentAttributeVideo(duration=duration, w=width, h=height, supports_streaming=True))
                    except:
                        thumb_path = None

                # Ensure thumb_path exists if we are going to use it
                actual_thumb = thumb_path if (thumb_path and os.path.exists(thumb_path)) else None

                print(f"[*] 📤 Uploading {os.path.basename(file_path)}...", flush=True)
                await client.send_file(
                    target, file_path, caption=caption, parse_mode='html',
                    progress_callback=_progress, attributes=attributes, thumb=actual_thumb
                )
                
                # Cleanup thumb
                if actual_thumb:
                    try: os.remove(actual_thumb)
                    except: pass
                
                print(f"\n[+] ✅ Upload complete!", flush=True)
                return True

            except FloodWaitError as e:
                print(f"\n[!] ⏳ TELEGRAM RATE LIMIT: Must wait {e.seconds} seconds...", flush=True)
                await client.disconnect()
                await asyncio.sleep(e.seconds + 5)
                continue # Retry this same file
            except Exception as e:
                print(f"\n[!] Upload error (Attempt {attempt+1}): {e}", flush=True)
                if "A wait of" in str(e): # Handle manual rate limits
                    import re
                    seconds = int(re.search(r'wait of (\d+)', str(e)).group(1))
                    await asyncio.sleep(seconds + 5)
            finally:
                await client.disconnect()
        
        return False

    import threading
    result = [False]
    def _thread_run():
        result[0] = asyncio.run(_run())

    t = threading.Thread(target=_thread_run, daemon=True)
    t.start()
    try:
        while t.is_alive(): t.join(timeout=1)
    except KeyboardInterrupt: raise
    return result[0]
