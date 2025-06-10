import os
import json
import logging
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logging.basicConfig(level=logging.INFO)

# Environment variables
SHOP_URL = os.getenv("SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("API_VERSION")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "#preorder-fall-2025"  # Change if using a different channel

STATE_FILE = ".slack_post_state.json"
client = WebClient(token=SLACK_BOT_TOKEN)


def fetch_published_fall_preorders():
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN
    }
    params = {"limit": 250}
    base_url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products.json"
    products = []

    while True:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code != 200:
            logging.error(f"Shopify API error: {response.text}")
            break
        data = response.json().get("products", [])
        products.extend(data)

        link_header = response.headers.get("Link")
        if link_header and 'rel="next"' in link_header:
            from urllib.parse import urlparse, parse_qs
            next_url = [part.split(";")[0].strip("<> ") for part in link_header.split(",") if 'rel="next"' in part][0]
            query = urlparse(next_url).query
            page_info = parse_qs(query).get("page_info", [None])[0]
            if not page_info:
                break
            params = {"limit": 250, "page_info": page_info}
        else:
            break

    matching = [
        p for p in products
        if any("Fall 2025" in tag or "preorder" in tag for tag in p.get("tags", "").split(","))
        and p.get("published_at")
    ]
    logging.info(f"{len(matching)} published Fall 2025/preorder products found")
    return matching


def build_message(published_products):
    if not published_products:
        return "❌ No Fall 2025 preorder titles have been published yet."

    message = "*📣 Published Fall 2025 Preorder Titles:*\n"
    for i, product in enumerate(published_products, start=1):
        title = product.get("title")
        handle = product.get("handle")
        scope = product.get("published_scope", "unknown").capitalize()
        message += f"{i}. *{title}* (`{handle}`) – Published to: {scope}\n"
    return message


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_or_create_message(channel_id, message_text):
    state = load_state()
    ts = state.get("message_ts")

    if ts:
        try:
            client.chat_update(channel=channel_id, ts=ts, text=message_text)
            logging.info("Message updated in Slack.")
        except SlackApiError as e:
            logging.error(f"Failed to update message: {e.response['error']}")
    else:
        try:
            response = client.chat_postMessage(channel=channel_id, text=message_text)
            ts = response["ts"]
            state["message_ts"] = ts
            save_state(state)
            logging.info("New message posted and state saved.")
        except SlackApiError as e:
            logging.error(f"Failed to post new message: {e.response['error']}")


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


def main():
    products = fetch_published_fall_preorders()
    message = build_message(products)
    channel_id = resolve_channel_id(SLACK_CHANNEL)
    if channel_id:
        get_or_create_message(channel_id, message)


if __name__ == "__main__":
    main()