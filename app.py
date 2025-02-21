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
JELLYFIN_MESSAGE = os.getenv("JELLYFIN_MESSAGE")
JELLYFIN_STOPPLAYBACK = os.getenv("JELLYFIN_STOPPLAYBACK")

if JELLYFIN_MESSAGE is None:
        JELLYFIN_MESSAGE = "Are you still watching?"
if JELLYFIN_STOPPLAYBACK is None:
       JELLYFIN_STOPPLAYBACK = "STOP"
        
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
            event = json.loads(request.data.decode('utf-8'))

        # Debugging: Log the parsed payload
        #print("Parsed Payload:", event)

        # Extract key information
        notification_type = event.get("NotificationType")
        user_id = event.get("UserId")
        device_id = event.get("DeviceId")
        item_type = event.get("ItemType")
        
        # Store session object with nullable fields
        session = {
            "NotificationUsername": event.get("NotificationUsername", None),
            "Id": event.get("Id", None), #T The ID of the session to stop
            "DeviceName": event.get("DeviceName", None),
            "RemoteEndPoint": event.get("RemoteEndPoint", None)
        }

        # Check if this is a "PlaybackStart" event for an episode
        if notification_type == "PlaybackStart": # and item_type == "Episode":
            key = f"{user_id}-{device_id}"

            print(f"ℹ️ PlaybackStart event received from user: {session.get('NotificationUsername', 'Unknown')}\n🌐 Device Address: {session.get('RemoteEndPoint', 'Unknown')}")

            if key not in playback_tracker:
                playback_tracker[key] = {
                    "count": 0,
                    "last_play_time": time.time()
                }

            tracker = playback_tracker[key]
            time_since_last_play = time.time() - tracker["last_play_time"]

            # Reset playback counter if Movie starts
            if item_type == "Movie":
                tracker["count"] = 0
                print(f"Movie started reset count for user: {session.get('NotificationUsername', 'Unknown')}")
                    
            # Reset the count if playback events are far apart (e.g., > 1 hour)
            if time_since_last_play > (60 * EPISODE_START_INTERVAL):
                tracker["count"] = 0

            # Increment the playback count
            if item_type == "Episode":
                tracker["count"] += 1
            tracker["last_play_time"] = time.time()

            print(f"ℹ️ {session.get('NotificationUsername', 'Unknown')} has played {tracker['count']} episodes in a row.")

            # If more than 4 episodes have been played, stop playback
            if tracker["count"] > (EPISODE_COUNT - 1):
                if stop_playback(session):
                    tracker["count"] = 0
                    return jsonify({"message": "Playback stopped due to autoplay limit"}), 200
                else:
                    return jsonify({"message": "Failed to stop playback"}), 500

    except Exception as e:
        print("Error processing webhook:", e)
        return jsonify({"message": "Error processing request"}), 500

    return jsonify({"message": "Event processed"}), 200


def stop_playback(session):
    """
    Stop playback for a given session ID using the Jellyfin API.
    """

    session_id = session['Id']
    display_message(session_id, JELLYFIN_MESSAGE, 'Sleep Timer', 7000)

    time.sleep(5)

    try:
        # Construct the URL to stop playback
        stop_url = f"{JELLYFIN_API_URL}/Sessions/{session_id}/Playing/Stop?ApiKey={JELLYFIN_API_TOKEN}"
        # Construct the URL to pause playback
        pause_url = f"{JELLYFIN_API_URL}/Sessions/{session_id}/Playing/Pause/?ApiKey={JELLYFIN_API_TOKEN}"
        
        # Send the request to stop playback
        req = urllib.request.urlopen(urllib.request.Request(stop_url, method="POST"))
        print(f"👤 {session.get('NotificationUsername', 'Unknown')} has played {int(EPISODE_COUNT)} episodes in a row.\n❗️ ⏹️ {JELLYFIN_STOPPLAYBACK} Playback ❗️\n🌐 Device Address: {session.get('RemoteEndPoint', 'Unknown')}")
        print()

        # Wait for 2 seconds before sending the next command
        time.sleep(2)

        # Construct the URL to send the 'GoHome' command
        go_home_url = f"{JELLYFIN_API_URL}/Sessions/{session_id}/Command/GoHome?ApiKey={JELLYFIN_API_TOKEN}"
        
        # Send the request to navigate back to the home screen
        if JELLYFIN_STOPPLAYBACK == "STOP":
            req = urllib.request.urlopen(urllib.request.Request(go_home_url, method="POST"))

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

    except Exception as e:
        print(f"Error sending display message to session {session_id}: {e}")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5553)
