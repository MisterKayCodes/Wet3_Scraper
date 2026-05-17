import sys
import os

# Ensure the app path is correct
sys.path.insert(0, r"C:\Kaycris\scraper")

from core.scraper import get_profile_data

def test():
    print("Testing get_profile_data on zeexhibitionist")
    content = get_profile_data("https://wet3.click/user/zeexhibitionist", max_pages=3, headless=True)
    print("Content found:", content)

if __name__ == "__main__":
    test()
