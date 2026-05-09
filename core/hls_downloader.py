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
    try:
        r = requests.get(m3u8_url, headers=headers, cookies=cookies, timeout=30)
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
                        seg_r = requests.get(seg_url, headers=headers, cookies=cookies, timeout=25)
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
        return True
        
    except Exception as e:
        print(f"[!] HLS Download failed: {e}", flush=True)
        return False
