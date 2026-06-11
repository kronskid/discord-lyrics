import os
import time
import threading
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- TINY WEB SERVER TO KEEP RENDER HAPPY & FREE ---
class KeepAliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Spotify Status Bot is Running!")

def run_web_server():
    # Render provides a PORT environment variable automatically
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveServer)
    print(f"Self-ping web server started on port {port}")
    server.serve_forever()

# --- DISCORD & SPOTIFY LOGIC ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOT_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOT_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOT_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

def update_discord_status(text):
    url = "https://discord.com/api/v9/users/@me/settings"
    headers = {"Authorization": DISCORD_TOKEN, "Content-Type": "application/json"}
    payload = {"custom_status": {"text": text, "emoji_name": "🎵"}}
    try:
        requests.patch(url, json=payload, headers=headers)
    except Exception:
        pass

def lyric_updater_loop():
    sp_oauth = SpotifyOAuth(
        client_id=SPOT_CLIENT_ID,
        client_secret=SPOT_CLIENT_SECRET,
        redirect_uri=SPOT_REDIRECT_URI,
        scope="user-read-currently-playing"
    )
    last_played_track = ""
    
    # Give the server a moment to boot
    time.sleep(5)
    
    while True:
        try:
            # 1. SELF-PING TRICK: Call our own web service URL to keep Render awake
            # (We will set the APP_URL variable in the dashboard later)
            app_url = os.getenv("APP_URL")
            if app_url:
                try:
                    requests.get(app_url)
                except Exception:
                    pass

            # 2. Check Spotify Status
            token_info = sp_oauth.get_cached_token()
            if token_info:
                sp = spotipy.Spotify(auth=token_info['access_token'])
                current_track = sp.current_user_playing()
                
                if current_track and current_track.get('is_playing'):
                    track_name = current_track['item']['name']
                    artist_name = current_track['item']['artists'][0]['name']
                    current_status_text = f"Listening to: {track_name} - {artist_name}"
                    
                    if current_status_text != last_played_track:
                        update_discord_status(current_status_text)
                        last_played_track = current_status_text
                else:
                    if last_played_track != "":
                        update_discord_status("")
                        last_played_track = ""
        except Exception:
            pass
            
        time.sleep(15) # Check Spotify every 15 seconds

if __name__ == "__main__":
    # Start the web server in a separate thread so it doesn't block the loop
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # Run our main updater loop
    lyric_updater_loop()
