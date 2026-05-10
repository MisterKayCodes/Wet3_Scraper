import requests
import os
from urllib.parse import urljoin
from tqdm import tqdm

def download_hls_stream(m3u8_url, output_path, headers=None, cookies=None, progress_callback=None):
    """
    Downloads an HLS stream (.m3u8) by fetching all segments and joining them.
    Pure Python alternative to ffmpeg.
    """
    print(f"[*] Starting HLS download (Pure Python Stitcher) for: {os.path.basename(output_path)}", flush=True)
    
    import config
    req_kwargs = {"headers": headers, "cookies": cookies, "timeout": 30}
    if config.USE_PROXY:
        req_kwargs["proxies"] = {"http": config.PROXY_SERVER, "https": config.PROXY_SERVER}

    try:
        r = requests.get(m3u8_url, **req_kwargs)
        r.raise_for_status()
        lines = r.text.splitlines()
        
        segments = []
        sub_playlists = []
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith("#"):
                continue
            if ".m3u8" in line:
                sub_playlists.append(urljoin(m3u8_url, line))
            else:
                segments.append(urljoin(m3u8_url, line))
        
        # If we found sub-playlists, we should probably follow the one with the highest bandwidth or just the first one
        if sub_playlists:
            print(f"[*] Found {len(sub_playlists)} sub-playlists. Choosing the best one...", flush=True)
            # Try the last one usually (often highest quality)
            return download_hls_stream(sub_playlists[-1], output_path, headers, cookies, progress_callback)

        if len(segments) < 5:
            print(f"[!] Warning: Playlist only has {len(segments)} segments. This might be a preview.", flush=True)
            # We'll still try, but we'll return a specific code so downloader can retry
            if not segments: return False
            
        print(f"[*] Found {len(segments)} segments. Stitching...", flush=True)
        
        with open(output_path, 'wb') as f:
            total_segs = len(segments)
            for i, seg_url in enumerate(tqdm(segments, desc="Stitching", unit="seg")):
                success = False
                for attempt in range(3):
                    try:
                        seg_kwargs = {"headers": headers, "cookies": cookies, "timeout": 25}
                        if config.USE_PROXY:
                            seg_kwargs["proxies"] = {"http": config.PROXY_SERVER, "https": config.PROXY_SERVER}
                        seg_r = requests.get(seg_url, **seg_kwargs)
                        seg_r.raise_for_status()
                        f.write(seg_r.content)
                        success = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            wait_time = 5 * (attempt + 1)
                            print(f"\n[!] Segment {i} failed ({e}). Retrying in {wait_time}s...", flush=True)
                            import time
                            time.sleep(wait_time)
                        else:
                            print(f"\n[!] Segment {i} FAILED after 3 attempts: {e}", flush=True)
                
                # Update progress every 5 segments to avoid flooding
                if progress_callback and i % 5 == 0:
                    progress_callback(i, total_segs)
                
                if not success:
                    continue
                    
        print(f"[SUCCESS] Stream saved to {output_path}", flush=True)
        if progress_callback: progress_callback(total_segs, total_segs)
        
        # --- FFMPEG REMUX: Convert raw .ts stitched file to proper .mp4 ---
        # This fixes the "blank video / audio only" issue on Telegram.
        # Without remuxing, Telegram can't read the video keyframe index.
        remuxed_path = output_path.replace('.mp4', '_remux.mp4')
        try:
            import subprocess
            import shutil
            import imageio_ffmpeg
            # PRIORITIZE SYSTEM FFmpeg (more stable on VPS)
            ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
            
            print(f"[*] Remuxing to proper MP4 container (Telegram-compatible)...", flush=True)
            result = subprocess.run(
                [ffmpeg_exe, "-y", "-i", output_path, "-c", "copy",
                 "-movflags", "+faststart", remuxed_path],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0 and os.path.exists(remuxed_path):
                os.replace(remuxed_path, output_path)  # Swap remuxed file in
                print(f"[+] Remux complete. File is now Telegram-compatible.", flush=True)
            else:
                print(f"[!] ffmpeg remux failed (returncode={result.returncode}). Keeping raw file.", flush=True)
                print(f"    stderr: {result.stderr[-300:]}", flush=True)
                if os.path.exists(remuxed_path): os.remove(remuxed_path)
        except Exception as e:
            print(f"[!] Remux error: {e}. Keeping raw file.", flush=True)
            if os.path.exists(remuxed_path): os.remove(remuxed_path)

        
        return True
        
    except Exception as e:
        print(f"[!] HLS Download failed: {e}", flush=True)
        return False
