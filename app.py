from flask import Flask, request, jsonify
import os
import time
import json
import requests
import urllib

JELLYFIN_API_URL = os.getenv("JELLYFIN_API_URL")
JELLYFIN_API_TOKEN = os.getenv("JELLYFIN_API_TOKEN")
EPISODE_START_INTERVAL = float(os.getenv("EPISODE_START_INTERVAL"))
EPISODE_COUNT = float(os.getenv("EPISODE_COUNT"))

app = Flask(__name__)

# In-memory tracking
playback_tracker = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Check the Content-Type header
        content_type = request.headers.get('Content-Type')
        
        if content_type == 'application/json':
            # Parse JSON payload
            event = request.json
        else:
            # Fall back to raw data and try to parse it
            print("Non-JSON Content-Type, attempting to parse raw data.")
            event = json.loads(request.data.decode('utf-8'))

        # Debugging: Log the parsed payload
        #print("Parsed Payload:", event)

        # Extract key information
        notification_type = event.get("NotificationType")
        user_id = event.get("UserId")
        device_id = event.get("DeviceId")
        item_type = event.get("ItemType")
        session_id = event.get("Id")  # Session ID to stop playback

        # Check if this is a "PlaybackStart" event for an episode
        if notification_type == "PlaybackStart" and item_type == "Episode":
            key = f"{user_id}-{device_id}"

            if key not in playback_tracker:
                playback_tracker[key] = {
                    "count": 0,
                    "last_play_time": time.time()
                }

            tracker = playback_tracker[key]
            time_since_last_play = time.time() - tracker["last_play_time"]

            # Reset the count if playback events are far apart (e.g., > 1 hour)
            if time_since_last_play > (60 * EPISODE_START_INTERVAL):
                tracker["count"] = 0

            # Increment the playback count
            tracker["count"] += 1
            tracker["last_play_time"] = time.time()

            print(f"User {user_id} on Device {device_id} has played {tracker['count']} episodes in a row.")

            # If more than 4 episodes have been played, stop playback
            if tracker["count"] > (EPISODE_COUNT - 1):
                if stop_playback(session_id):
                    tracker["count"] = 0
                    return jsonify({"message": "Playback stopped due to autoplay limit"}), 200
                else:
                    return jsonify({"message": "Failed to stop playback"}), 500

    except Exception as e:
        print("Error processing webhook:", e)
        return jsonify({"message": "Error processing request"}), 500

    return jsonify({"message": "Event processed"}), 200


def stop_playback(session_id):
    """
    Stop playback for a given session ID using the Jellyfin API.
    """

    display_message(session_id, 'Stopping Playback', 'Sleep Timer', 7000)

    time.sleep(5)

    try:
        # Construct the URL to stop playback
        stop_url = f"{JELLYFIN_API_URL}/Sessions/{session_id}/Playing/Stop?ApiKey={JELLYFIN_API_TOKEN}"
        
        # Send the request to stop playback
        req = urllib.request.urlopen(urllib.request.Request(stop_url, method="POST"))
        print(f"Playback stopped for session {session_id}")

        # Wait for 2 seconds before sending the next command
        time.sleep(2)

        # Construct the URL to send the 'GoHome' command
        go_home_url = f"{JELLYFIN_API_URL}/Sessions/{session_id}/Command/GoHome?ApiKey={JELLYFIN_API_TOKEN}"
        
        # Send the request to navigate back to the home screen
        req = urllib.request.urlopen(urllib.request.Request(go_home_url, method="POST"))
        print(f"GoHome command sent for session {session_id}")

        return True
    except Exception as e:
        print(f"Error stopping playback for session {session_id}: {e}")
        return False

def display_message(session_id, message, header="Notice", timeout_ms=5000):
    """
    Send a display message to the Jellyfin client.
    
    Args:
        session_id (str): The session ID of the client.
        message (str): The message to display.
        header (str): The header for the message.
        timeout_ms (int): Time in milliseconds to display the message.
    """

    try:
        # Construct the URL for the DisplayMessage command
        display_message_url = f"{JELLYFIN_API_URL}/Sessions/{session_id}/Command"
        headers = {
            "Authorization": f"MediaBrowser Token={JELLYFIN_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "Name": "DisplayMessage",
            "Arguments": {
                "Header": header,
                "Text": message,
                "TimeoutMs": timeout_ms
            }
        }

        # Send the display message
        req = urllib.request.Request(display_message_url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        urllib.request.urlopen(req)
        print(f"Message sent to session {session_id}: {message}")

    except Exception as e:
        print(f"Error sending display message to session {session_id}: {e}")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5553)
