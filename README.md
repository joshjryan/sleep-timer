# sleep-timer
A poor man's sleep timer for Jellyfin

## Summary
Becasue most Jellyfin clients do not have a "Still Watching?" feature, I created a work-around.  This app leverages events from the official Jellyfin Webhook Plugin to count the number of episodes that any user has played on a specific device.  If more than 3 episodes have been played with less than one hour between start times, this will automatically stop playback of the fourth one.

## Requirements
1. Start the docker container
2. Install the [Jellyfin Webhook Plugin](https://github.com/jellyfin/jellyfin-plugin-webhook)
3. Add a generic destination, with a Webhook URL of `http://{docker-address}:5553/webhook`
4. Choose the "Playback Start" Notification Type and choose the users who will use this sleep timer


## Docker Compose Example

Here is an example of how to use `sleep-timer` with Docker Compose:

```yaml
version: '3.8'

services:
  sleep-timer:
    image: joshjryan/jf-sleep-timer:latest
    container_name: jf-sleep-timer
    ports:
      - "5553:5553"
    environment:
        # Required. Address of your jellyfin server (e.g. http://192.168.1.100:8096)
      - JELLYFIN_API_URL=value1
        # Required. API Key generated from your jellyfin server
      - JELLYFIN_API_TOKEN=value2
```
