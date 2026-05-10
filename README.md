# Wet3 Scraping Optimization and Automation

This project implements a robust, modular pipeline for automating the extraction and assembly of media content from wet3.click. The system is designed to handle aggressive ad-walls, dynamic pagination, and fragmented HLS video streams, providing a seamless interface via a Telegram bot.

## 🛠 Troubleshooting & Anti-Bot Bypass

If the bot encounters a "Blank Screen" or "Timeout" during scraping:

### 1. Manual Session Hijacking (Recommended)
The most reliable way to bypass ad-walls is to "lend" your human session to the bot.
1. Run the capture tool: `python scripts/capture_session.py`
2. A browser window will open. Log in manually and solve any challenges.
3. Press Enter in the terminal to save the session.
4. Restart the bot: `python bot/main_bot.py`

### 2. Visible Debugging
The bot is currently set to **Visible Mode** (`headless=False`) in `bot/handlers.py`. This allows you to watch exactly what is happening. If it's working well, you can switch it back to `True` for background operation.

### 3. VPS Deployment
On a VPS, ensure you have a "fake screen" (Xvfb) or use a proxy like Cloudflare WARP.
- Install WARP: `config.USE_PROXY = True`
- Run via Xvfb: `xvfb-run python bot/main_bot.py`

## Project Architecture

The codebase follows a service-oriented architecture to ensure maintainability and scalability.

- **bot/**: A hybrid Telegram interface utilizing **Aiogram v3** for command handling and **Telethon** as an MTProto worker.
- **services/**: Orchestration layer managing the workflow between scraping and downloading.
- **core/**: Low-level engines for browser automation, HLS stitching, and media resolution.
- **utils/**: Cross-cutting helpers for settings management and browser interaction.
- **data/**: Local storage for scraped metadata and persistent configurations.

## Hybrid Bot Architecture

This system leverages a dual-layered Telegram integration:
1. **Interactive UI (Aiogram v3)**: Dedicated Bot Token for high-speed commands and state management.
2. **Media Worker (Telethon)**: MTProto session to bypass the 50MB upload limit, supporting files up to 2GB.

## Available Commands

- `/start`: Initializes the bot and shows the premium command menu.
- `/scrape [URL]`: Scrapes a Wet3 profile and provides download options.
- `/set_channel [Link]`: Dynamically sets the target channel for media relay.
- `/test_target`: Sends a self-deleting message to verify channel permissions.
- `/status`: Displays system health (CPU, RAM, and current configuration).

## Key Features

- **Evidence-Based Navigation**: Utilizes UI-driven verification to handle dynamic pagination, ensuring no content is skipped due to DOM latency.
- **Surgical ID Targeting**: Employs direct DOM element targeting to bypass transparent ad-overlays and modal interceptions.
- **Self-Healing HLS Stitcher**: A resilient stream downloader that handles server-side connection resets and timeouts with an automated retry and back-off mechanism.
- **Interactive Bot Interface**: Remote control of the scraping process through Telegram, featuring real-time progress bars and selective download modes.

## Installation

### Prerequisites
- Python 3.10 or higher
- ffmpeg (required for HLS segment stitching)
- Chrome/Chromium browser (managed via Playwright)

### Setup
1. Clone the repository and navigate to the project root.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Configuration:
   - Rename `.env.example` to `.env`.
   - Fill in your Telegram API credentials and target channel link.
   - For the `SESSION_STRING`, use a Telethon utility script to generate one if you haven't already.

## Usage

Start the Hybrid Assistant to begin remote operations:

```bash
python bot/hybrid_bot.py
```

### Operational UX
- **Command `/set_channel [Link]`**: Dynamically update the destination for uploads without restarting the bot.
- **Command `/scrape [URL]`**: Initiates a background profile analysis.
- **Interactive UI**: Follow the on-screen buttons to select download volumes (1, 10, or ALL).
- **Progress Monitoring**: Observe real-time stitching progress bars directly within the Telegram chat.

## Development and Contributions

This project is structured for expansion. Developers adding new extraction logic should implement it within the `core/scraper.py` module and expose it through the `ScrapeOrchestrator` service to maintain bot compatibility.
