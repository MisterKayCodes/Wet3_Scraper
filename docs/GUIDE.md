# System Operations Guide

This document outlines the operational flow and user experience (UX) for managing the scraping and download pipeline.

## User Experience Flow

The system is designed to be managed entirely through Telegram, allowing for remote operation without direct terminal access.

### 1. Analysis Phase
- **Input**: The user sends the command `/scrape` followed by the target profile URL.
- **Process**: The bot triggers a headless browser instance. It navigates through all available pages of the profile, identifying the "Page X of Y" indicators to verify progress.
- **Output**: The bot returns a summary of the findings (total items, split between videos and images) and presents interactive buttons for the next action.

### 2. Selection Phase
- **Action**: The user selects a download mode via the inline buttons:
    - **Download 1**: Fetches only the most recent item.
    - **Download 10**: Fetches the first ten items.
    - **Download ALL**: Processes the entire library.
- **Verification**: The bot acknowledges the selection and initializes the download queue.

### 3. Extraction and Stitching Phase
- **Resolution**: For each item, the system resolves the underlying media source, bypassing monetization redirects.
- **Stitching**: If the source is an HLS stream, the system begins downloading segments. The user receives real-time updates via a progress bar in the Telegram message.
- **Resilience**: If the host resets the connection, the system waits for a defined back-off period and retries the specific segment.

### 4. Relay Phase
- **Delivery**: Once a file is successfully assembled locally, it is uploaded to the designated Telegram channel.
- **Cleanup**: The local temporary file is removed (if configured) to maintain storage efficiency on the host machine.

## Configuration Management

Settings are managed via `config.py` at the project root. This file pulls from the `.env` file but allows for global overrides of directory paths and headless operation modes.

## Technical Maintenance

Logs are stored in the `test_output/` directory for debugging. If the bot fails to resolve a link, check the latest debug screenshots saved in the root directory to identify if an ad-wall or Cloudflare challenge has changed.
