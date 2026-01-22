# toolTruyen Downloader

## Overview
A Python Flask web application for downloading novels from Vietnamese web novel sites. The app scrapes chapters from novel websites and downloads them into a single HTML file.

## Project Structure
- `main.py` - Core scraping logic with functions for getting chapter lists and downloading content
- `web/` - Flask web application
  - `app.py` - Flask routes and API endpoints
  - `templates/index.html` - Main UI template
  - `static/style.css` - Styling
- `requirements.txt` - Python dependencies

## Key Features
- Load chapter list from novel URL
- Select chapter range for download
- Real-time progress logging
- Stop/resume download functionality

## Running the Application
The Flask server runs on `0.0.0.0:5000`.

## Dependencies
- Flask - Web framework
- requests - HTTP client
- beautifulsoup4 - HTML parsing
- lxml, html5lib - Parser backends
- selenium, webdriver-manager - For dynamic content loading

## Recent Changes
- 2026-01-22: Initial setup for Replit environment, configured Flask to run on port 5000
