import os
import json
import time
from downloader import process_video_queue

# Quick test for persistent session on a small list
TEST_VIDEOS = [
    {
        "title": "Eastsidegoddess Test 1", 
        "link": "https://nelb6o.wet3.click/api/get-monetized-link?id=86859&token=eyJ1IjoiaHR0cHM6Ly91Y2FyZWNkbi5jb20vOTBhMzAxMWItYzlkMi00ZTlmLWJiZWEtODAyNGI4ZTRjYTIzLyIsInQiOiIyIiwiaSI6ODg0NDAsInRoIjoiL2FwaS9pbWFnZS84ODQ0MCIsIm4iOiJNYWxpeWFvZmZpY2lhbCJ9"
    }
]

if __name__ == "__main__":
    print("--- Verifying Optimized Downloader ---", flush=True)
    if not os.path.exists("session.json"):
        print("[!] No session.json found. Test might fail on Cloudflare.", flush=True)
    
    # Process the queue
    process_video_queue(TEST_VIDEOS)
    
    # Check
    files = os.listdir("videos")
    if any("Eastsidegoddess_Test_1" in f for f in files):
        print("\n[SUCCESS] Optimized Downloader verified!", flush=True)
    else:
        print("\n[FAILURE] Download did not complete.", flush=True)
