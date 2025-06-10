import os
import requests
from slack_sdk.webhook import WebhookClient

SHOP_URL = os.getenv("SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("API_VERSION")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def fetch_unpublished_fall_preorders():
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products.json"
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN
    }
    response = requests.get(url, headers=headers, params={"limit": 250})
    products = response.json().get("products", [])

    return [
        (p["title"], p["handle"])
        for p in products
        if any("Fall 2025" in tag or "preorder" in tag for tag in p.get("tags", "").split(","))
        and not p.get("published_at")
    ]

def post_to_slack(unpublished):
    if not unpublished:
        msg = "✅ All Fall 2025 preorder titles are published."
    else:
        body = "\n".join([f"{i+1}. *{title}* (`{handle}`)" for i, (title, handle) in enumerate(unpublished)])
        msg = f"""📌 *[UNPUBLISHED TITLES – FALL 2025]*  
The following titles are still unpublished:

{body}

Use this thread to update status or tag teammates.
"""
    webhook = WebhookClient(SLACK_WEBHOOK_URL)
    webhook.send(text=msg)

def main():
    unpublished = fetch_unpublished_fall_preorders()
    post_to_slack(unpublished)

if __name__ == "__main__":
    main()