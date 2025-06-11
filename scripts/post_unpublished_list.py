import os
import json
import requests
import logging
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logging.basicConfig(level=logging.INFO)

SHOP_URL = os.getenv("SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("API_VERSION")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "#preorder-fall-2025"

client = WebClient(token=SLACK_BOT_TOKEN)


def fetch_unpublished_fall_preorders():
    all_unpublished = []
    base_url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products.json"
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN
    }
    params = {"limit": 250}

    while True:
        response = requests.get(base_url, headers=headers, params=params)
        products = response.json().get("products", [])
        for p in products:
            tags = [tag.strip() for tag in p.get("tags", "").split(",")]
            if ("Fall 2025" in tags and "preorder" in tags) and not p.get("published_at"):
                all_unpublished.append((p["title"], p["handle"]))
                time.sleep(0.6)

        link_header = response.headers.get("Link")
        if link_header and 'rel="next"' in link_header:
            next_url = [
                part.split(";")[0].strip("<> ")
                for part in link_header.split(",")
                if 'rel="next"' in part
            ][0]
            from urllib.parse import urlparse, parse_qs
            query = urlparse(next_url).query
            page_info = parse_qs(query).get("page_info", [None])[0]
            if not page_info:
                break
            params = {"limit": 250, "page_info": page_info}
        else:
            break

    return all_unpublished


def build_message(unpublished):
    if not unpublished:
        return "✅ All Fall 2025 preorder titles are published."

    body = "\n".join([f"{i+1}. *{title}*" for i, (title, handle) in enumerate(unpublished)])
    return f"""*UNPUBLISHED TITLES - FALL 2025*  
The following titles are still unpublished:

{body}
"""




def resolve_channel_id(channel_name):
    try:
        response = client.conversations_list()
        for channel in response["channels"]:
            if channel["name"] == channel_name.strip("#"):
                return channel["id"]
        logging.error(f"Channel {channel_name} not found.")
    except SlackApiError as e:
        logging.error(f"Error fetching channel list: {e.response['error']}")
    return None



# New message tracking functions using conversation history
def find_existing_message(channel_id):
    try:
        result = client.conversations_history(channel=channel_id, limit=50)
        for message in result["messages"]:
            if message.get("text", "").startswith("*UNPUBLISHED TITLES - FALL 2025*"):
                return message["ts"]
    except SlackApiError as e:
        logging.error(f"Failed to fetch conversation history: {e.response['error']}")
    return None

def post_or_update_message(channel_id, message_text):
    existing_ts = find_existing_message(channel_id)
    if existing_ts:
        try:
            client.chat_update(channel=channel_id, ts=existing_ts, text=message_text)
            logging.info("Updated existing Slack message.")
        except SlackApiError as e:
            logging.error(f"Failed to update message: {e.response['error']}")
    else:
        try:
            client.chat_postMessage(channel=channel_id, text=message_text)
            logging.info("Posted new Slack message.")
        except SlackApiError as e:
            logging.error(f"Failed to post message: {e.response['error']}")


def main():
    unpublished = fetch_unpublished_fall_preorders()
    message = build_message(unpublished)
    channel_id = resolve_channel_id(SLACK_CHANNEL)
    if channel_id:
        post_or_update_message(channel_id, message)


if __name__ == "__main__":
    main()