import os
import sys
import time
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://nelb6o.wet3.click"

def get_categories():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL)
        
        # Give it a second to load footer
        time.sleep(2)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Based on subagent report: a[href^="/categories/"]
        category_links = soup.select('a[href^="/categories/"]')
        categories = []
        for link in category_links:
            name = link.get_text(strip=True)
            href = link['href']
            if name and href:
                categories.append({"name": name, "url": BASE_URL + href if not href.startswith("http") else href})
        
        browser.close()
        return categories

if __name__ == "__main__":
    print("[*] Fetching categories...", flush=True)
    cats = get_categories()
    for i, cat in enumerate(cats):
        print(f"{i+1}. {cat['name']} ({cat['url']}, flush=True)")
    
    with open("categories.json", "w") as f:
        json.dump(cats, f, indent=4)
    print(f"\n[+] Saved {len(cats, flush=True)} categories to categories.json")
