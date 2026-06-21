# BigQuery Release Pulse

A lightweight, full-stack RSS Feed tracker and sharing application for Google Cloud BigQuery release notes. It features a modern, responsive web dashboard built with Flask, vanilla JavaScript, and customized CSS.

---

## 🚀 Features

- **Google Feed Integration**: Automatically fetches, parses, and formats the official BigQuery release notes Atom/RSS XML feed.
- **Aggressive In-Memory Caching**: Caches parsed results for 10 minutes to minimize external calls and maximize performance.
- **Smart Parsing**: Uses `DOMParser` on the client side to break down massive daily update blocks into individual, atomic release cards.
- **Real-Time Search & Filters**: Search release notes by keyword or filter updates dynamically by category (e.g., *Feature*, *Announcement*, *Changed*, *Issue*).
- **Interactive Multi-Select Dashboard**: Select multiple updates to compile a summary or prepare social media updates.
- **Custom Twitter/X Composer**: Draft tweets with a live mockup preview. The character counter accurately handles links (counting each as exactly 23 characters) and warns if the 280-character limit is exceeded.
- **Graceful Degradation**: Backend defaults to cached entries if the upstream RSS feed is temporarily unreachable.

---

## 🛠️ Project Structure

```
bq-release-notes/
├── app.py                 # Flask server, RSS feed fetching & parser, cache manager
├── requirements.txt       # Python package dependencies
├── .gitignore             # Ignored files (venv, caches, IDE configs)
├── templates/
│   └── index.html         # Main dashboard markup shell
└── static/
    ├── css/style.css      # Dark-mode styling, glassmorphism UI rules
    └── js/app.js          # Core frontend state engine & client logic
```

---

## 💻 Setup and Run Locally

### 1. Prerequisites
Ensure you have **Python 3.8+** installed.

### 2. Clone and Initialize Environment
Navigate to the project root directory and set up a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (Command Prompt):
venv\Scripts\activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
Install the required packages:
```bash
pip install -r requirements.txt
```

### 4. Run the Application
Start the Flask development server:
```bash
python app.py
```
The application will run locally at [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 📡 API Endpoints

### `GET /api/releases`
Fetches and returns the formatted release updates.
* **Query Parameters**:
  - `refresh=true` (optional): Forces the server to bypass the in-memory cache and fetch the feed fresh from Google.
