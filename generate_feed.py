"""
Script kay-jbed les produits li rayjine (hot products) mn AliExpress Affiliate API
w kay-sawb feed.csv li Meta (Facebook) katkra mno l Dynamic Catalog Ads.
"""

import hashlib
import time
import csv
import os
import requests

APP_KEY = os.environ.get("ALIEXPRESS_APP_KEY")
APP_SECRET = os.environ.get("ALIEXPRESS_APP_SECRET")
TRACKING_ID = os.environ.get("ALIEXPRESS_TRACKING_ID")

API_URL = "https://api-sg.aliexpress.com/sync"


def generate_sign(params: dict, secret: str) -> str:
    sorted_items = sorted(params.items())
    base_string = secret + "".join(f"{k}{v}" for k, v in sorted_items) + secret
    return hashlib.md5(base_string.encode("utf-8")).hexdigest().upper()


def call_api(method: str, extra_params: dict) -> dict:
    params = {
        "app_key": APP_KEY,
        "method": method,
        "sign_method": "md5",
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
    }
    params.update({k: v for k, v in extra_params.items() if v is not None})
    params["sign"] = generate_sign(params, APP_SECRET)

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_hot_products(page_no: int = 1, page_size: int = 50, category_id: str = None) -> list:
    extra = {
        "tracking_id": TRACKING_ID,
        "page_no": page_no,
        "page_size": page_size,
        "target_currency": "USD",
        "target_language": "AR",
        "ship_to_country": "MA",
        "category_ids": category_id,
    }
    data = call_api("aliexpress.affiliate.hotproduct.query", extra)

    try:
        resp = data["aliexpress_affiliate_hotproduct_query_response"]
        products = resp["resp_result"]["result"]["products"]["product"]
        if isinstance(products, dict):
            products = [products]
        return products
    except (KeyError, TypeError):
        print("Ma jatch l response b shakl mnataR. Hada howa li rja3 l API:")
        print(data)
        return []


def build_feed(products: list, output_path: str = "feed.csv") -> None:
    fieldnames = [
        "id",
        "title",
        "description",
        "availability",
        "condition",
        "price",
        "link",
        "image_link",
        "brand",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for p in products:
            product_id = p.get("product_id", "")
            title = (p.get("product_title", "") or "")[:150]
            price = p.get("target_sale_price", p.get("target_app_sale_price", ""))
            currency = p.get("target_sale_price_currency", "USD")
            image = p.get("product_main_image_url", "")
            link = p.get("promotion_link", p.get("product_detail_url", ""))

            writer.writerow(
                {
                    "id": product_id,
                    "title": title,
                    "description": title,
                    "availability": "in stock",
                    "condition": "new",
                    "price": f"{price} {currency}",
                    "link": link,
                    "image_link": image,
                    "brand": "AliExpress",
                }
            )

    print(f"Tsawb {output_path} b {len(products)} produits.")


if __name__ == "__main__":
    if not all([APP_KEY, APP_SECRET, TRACKING_ID]):
        raise SystemExit(
            "Khassek dir ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET w ALIEXPRESS_TRACKING_ID "
            "f environment variables (ola GitHub Secrets) qbel matshaggl had script."
        )

    all_products = []
    for page in range(1, 4):
        page_products = get_hot_products(page_no=page)
        if not page_products:
            break
        all_products.extend(page_products)

    build_feed(all_products, output_path="feed.csv")
