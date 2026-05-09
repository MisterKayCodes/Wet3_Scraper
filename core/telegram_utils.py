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
