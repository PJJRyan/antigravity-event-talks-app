import os
import time
import requests
import feedparser
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

FEED_URL = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"
CACHE_EXPIRY = 600  # Cache feed for 10 minutes (600 seconds)
feed_cache = {
    "data": None,
    "last_fetched": 0
}

def fetch_and_parse_feed(force=False):
    """
    Fetches the BigQuery release notes RSS/Atom feed and parses it.
    Uses in-memory caching unless force is True.
    """
    now = time.time()
    
    # Return cached data if it's still fresh and we aren't forcing a refresh
    if not force and feed_cache["data"] and (now - feed_cache["last_fetched"]) < CACHE_EXPIRY:
        return feed_cache["data"], True
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/xml, text/xml, */*"
    }
    
    try:
        response = requests.get(FEED_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        feed = feedparser.parse(response.text)
        
        # Check if parsing was successful and entries exist
        if not feed.entries and feed.bozo:
            # Bozo is set to 1 if the XML is not well-formed
            raise Exception(f"Failed to parse XML: {feed.bozo_exception}")
            
        entries = []
        for entry in feed.entries:
            # Extract content from 'content' or 'summary'
            content_val = ""
            if entry.get("content"):
                content_val = entry.content[0].value
            elif entry.get("summary"):
                content_val = entry.summary
                
            entries.append({
                "id": entry.get("id", ""),
                "title": entry.get("title", "No Date"),  # The date is the title in Google's release notes feed
                "link": entry.get("link", ""),
                "published": entry.get("published") or entry.get("updated") or "",
                "content": content_val
            })
            
        # Update cache
        feed_cache["data"] = entries
        feed_cache["last_fetched"] = now
        return entries, False
        
    except Exception as e:
        # If fetching fails but we have cached data, return the cached data (graceful degradation)
        if feed_cache["data"]:
            return feed_cache["data"], True
        raise e

@app.route('/')
def index():
    """Renders the main web interface."""
    return render_template('index.html')

@app.route('/api/releases')
def get_releases():
    """
    API endpoint that returns the release notes.
    Accepts query parameter '?refresh=true' to force-refresh the feed.
    """
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        entries, from_cache = fetch_and_parse_feed(force=force_refresh)
        return jsonify({
            "status": "success",
            "from_cache": from_cache,
            "count": len(entries),
            "data": entries
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    # Listen on localhost:5000 by default
    app.run(host='127.0.0.1', port=5000, debug=True)
