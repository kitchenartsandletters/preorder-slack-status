import os
import requests
from slack_sdk.webhook import WebhookClient

SHOP_URL = os.getenv("SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("API_VERSION")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

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
            if ("Fall 2025" in tags or "preorder" in tags) and not p.get("published_at"):
                all_unpublished.append((p["title"], p["handle"]))

        link_header = response.headers.get("Link")
        if link_header and 'rel="next"' in link_header:
            # Extract page_info from the link header
            next_url = [
                part.split(";")[0].strip("<> ")
                for part in link_header.split(",")
                if 'rel="next"' in part
            ][0]
            # Extract query params from next_url
            from urllib.parse import urlparse, parse_qs
            query = urlparse(next_url).query
            page_info = parse_qs(query).get("page_info", [None])[0]
            if not page_info:
                break
            params = {"limit": 250, "page_info": page_info}
        else:
            break

    return all_unpublished

def post_to_slack(unpublished):
    if not unpublished:
        msg = "✅ All Fall 2025 preorder titles are published."
    else:
        body = "\n".join([f"{i+1}. *{title}* (`{handle}`)" for i, (title, handle) in enumerate(unpublished)])
        msg = f"""📌 *[UNPUBLISHED TITLES – FALL 2025]*  
The following titles are still unpublished:

{body}

"""
    webhook = WebhookClient(SLACK_WEBHOOK_URL)
    webhook.send(text=msg)

def main():
    unpublished = fetch_unpublished_fall_preorders()
    post_to_slack(unpublished)

if __name__ == "__main__":
    main()