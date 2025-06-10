import os
import requests
from slack_sdk.webhook import WebhookClient
import logging

logging.basicConfig(level=logging.INFO)

SHOP_URL = os.getenv("SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("API_VERSION")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def fetch_published_fall_preorders():
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products.json"
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN
    }
    response = requests.get(url, headers=headers, params={"limit": 250})
    products = response.json().get("products", [])
    logging.info(f"Fetched {len(products)} total products")
    filtered = [
        p for p in products
        if any("Fall 2025" in tag or "preorder" in tag for tag in p.get("tags", "").split(","))
        and p.get("published_at")
    ]
    logging.info(f"{len(filtered)} products match Fall 2025/preorder and are published")
    return filtered

def format_publication_message(product):
    return f"""📣 *New Publication – Fall 2025*

*{product['title']}*
• Published to: {product.get('published_scope', 'unknown').capitalize()}
• Handle: `{product['handle']}`
"""

def post_to_slack(message):
    logging.info("Posting to Slack:\n" + message)
    webhook = WebhookClient(SLACK_WEBHOOK_URL)
    webhook.send(text=message)

def main():
    published = fetch_published_fall_preorders()
    for product in published:
        msg = format_publication_message(product)
        post_to_slack(msg)

if __name__ == "__main__":
    main()