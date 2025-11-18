import requests
import json
import random
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("AMPLITUDE_API_KEY")
if not API_KEY:
    raise ValueError("AMPLITUDE_API_KEY not set in .env")

API_URL = "https://api2.amplitude.com/2/httpapi"

# Simulace různých uživatelů
DEVICE_IDS = [f"device_{i:04d}" for i in range(1, 1001)]  # 1000 různých uživatelů
USER_IDS = [f"user_{i:04d}" for i in range(1, 1001)]

# Různé typy událostí pro e-commerce aplikaci
EVENT_TYPES = [
    "Sign up",
    "Login",
    "View Product",
    "Add to Cart",
    "Remove from Cart",
    "Start Checkout",
    "Complete Purchase",
    "View Category",
    "Search",
    "Share Product",
    "Add to Wishlist",
    "Rate Product",
    "Logout"
]

# Ukázkové produkty
PRODUCTS = [
    {"id": "prod_001", "name": "Wireless Headphones", "category": "Electronics", "price": 79.99},
    {"id": "prod_002", "name": "Running Shoes", "category": "Sports", "price": 129.99},
    {"id": "prod_003", "name": "Coffee Maker", "category": "Home", "price": 89.99},
    {"id": "prod_004", "name": "Laptop Backpack", "category": "Accessories", "price": 49.99},
    {"id": "prod_005", "name": "Yoga Mat", "category": "Sports", "price": 29.99},
    {"id": "prod_006", "name": "Smart Watch", "category": "Electronics", "price": 299.99},
    {"id": "prod_007", "name": "Water Bottle", "category": "Sports", "price": 19.99},
    {"id": "prod_008", "name": "Desk Lamp", "category": "Home", "price": 39.99},
    {"id": "prod_009", "name": "Bluetooth Speaker", "category": "Electronics", "price": 59.99},
    {"id": "prod_010", "name": "Tennis Racket", "category": "Sports", "price": 149.99},
    {"id": "prod_011", "name": "Kitchen Knife Set", "category": "Home", "price": 99.99},
    {"id": "prod_012", "name": "Sunglasses", "category": "Accessories", "price": 89.99},
    {"id": "prod_013", "name": "Gaming Mouse", "category": "Electronics", "price": 69.99},
    {"id": "prod_014", "name": "Dumbbells Set", "category": "Sports", "price": 79.99},
    {"id": "prod_015", "name": "Air Purifier", "category": "Home", "price": 199.99},
    {"id": "prod_016", "name": "Leather Wallet", "category": "Accessories", "price": 39.99},
    {"id": "prod_017", "name": "Webcam HD", "category": "Electronics", "price": 89.99},
    {"id": "prod_018", "name": "Resistance Bands", "category": "Sports", "price": 24.99},
    {"id": "prod_019", "name": "Blender", "category": "Home", "price": 69.99},
    {"id": "prod_020", "name": "Phone Case", "category": "Accessories", "price": 19.99},
    {"id": "prod_021", "name": "Mechanical Keyboard", "category": "Electronics", "price": 129.99},
    {"id": "prod_022", "name": "Basketball", "category": "Sports", "price": 34.99},
    {"id": "prod_023", "name": "Toaster", "category": "Home", "price": 49.99},
    {"id": "prod_024", "name": "Travel Pillow", "category": "Accessories", "price": 29.99},
    {"id": "prod_025", "name": "Tablet 10 inch", "category": "Electronics", "price": 349.99},
    {"id": "prod_026", "name": "Camping Tent", "category": "Sports", "price": 179.99},
    {"id": "prod_027", "name": "Vacuum Cleaner", "category": "Home", "price": 229.99},
    {"id": "prod_028", "name": "Backpack Mini", "category": "Accessories", "price": 34.99},
    {"id": "prod_029", "name": "USB-C Hub", "category": "Electronics", "price": 44.99},
    {"id": "prod_030", "name": "Bicycle Helmet", "category": "Sports", "price": 54.99},
]

CATEGORIES = ["Electronics", "Sports", "Home", "Accessories"]
PLATFORMS = ["iOS", "Android", "Web"]
COUNTRIES = ["CZ", "SK", "US", "UK", "DE"]


def generate_timestamp(days_ago=0, hours_ago=0):
    """Generuje timestamp pro události v minulosti"""
    time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
    return int(time.timestamp() * 1000)


def send_events(events):
    """Odešle události do Amplitude"""
    headers = {
        'Content-Type': 'application/json',
        'Accept': '*/*'
    }

    data = {
        "api_key": API_KEY,
        "events": events
    }

    response = requests.post(API_URL, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Odesláno {len(events)} událostí - Status: {result}")
    else:
        print(f"✗ Chyba: {response.status_code} - {response.text}")

    return response.status_code == 200


def create_user_journey(device_id, user_id, day_offset):
    """Vytvoří realistickou cestu uživatele"""
    events = []
    base_time = day_offset

    # Společné user properties
    platform = random.choice(PLATFORMS)
    country = random.choice(COUNTRIES)

    # 1. Sign up (pouze pro některé uživatele)
    if random.random() < 0.3:  # 30% nových uživatelů
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Sign up",
            "time": generate_timestamp(days_ago=base_time),
            "platform": platform,
            "user_properties": {
                "country": country,
                "signup_method": random.choice(["email", "google", "facebook"])
            }
        })

    # 2. Login
    events.append({
        "device_id": device_id,
        "user_id": user_id,
        "event_type": "Login",
        "time": generate_timestamp(days_ago=base_time, hours_ago=-1),
        "platform": platform,
        "user_properties": {
            "country": country
        }
    })

    # 3. Prohlížení kategorií a produktů
    num_products_viewed = random.randint(3, 15)
    for i in range(num_products_viewed):
        product = random.choice(PRODUCTS)
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "View Product",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-1 - i * 0.1),
            "platform": platform,
            "event_properties": {
                "product_id": product["id"],
                "product_name": product["name"],
                "category": product["category"],
                "price": product["price"]
            }
        })

    # 4. View Category
    if random.random() < 0.5:
        category = random.choice(CATEGORIES)
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "View Category",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-1.5),
            "platform": platform,
            "event_properties": {
                "category": category
            }
        })

    # 5. Někdy hledání
    if random.random() < 0.4:
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Search",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-2),
            "platform": platform,
            "event_properties": {
                "search_query": random.choice(["headphones", "shoes", "watch", "yoga", "coffee", "bluetooth", "backpack"])
            }
        })

    # 6. Wishlist a rating
    if random.random() < 0.3:
        wishlist_product = random.choice(PRODUCTS)
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Add to Wishlist",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-2.2),
            "platform": platform,
            "event_properties": {
                "product_id": wishlist_product["id"],
                "product_name": wishlist_product["name"],
                "price": wishlist_product["price"]
            }
        })

    if random.random() < 0.2:
        rated_product = random.choice(PRODUCTS)
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Rate Product",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-2.5),
            "platform": platform,
            "event_properties": {
                "product_id": rated_product["id"],
                "product_name": rated_product["name"],
                "rating": random.randint(3, 5)
            }
        })

    if random.random() < 0.15:
        shared_product = random.choice(PRODUCTS)
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Share Product",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-2.7),
            "platform": platform,
            "event_properties": {
                "product_id": shared_product["id"],
                "product_name": shared_product["name"],
                "share_method": random.choice(["facebook", "twitter", "email", "copy_link"])
            }
        })

    # 7. Přidání do košíku
    cart_items = random.sample(PRODUCTS, random.randint(1, 3))
    for item in cart_items:
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Add to Cart",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-3),
            "platform": platform,
            "event_properties": {
                "product_id": item["id"],
                "product_name": item["name"],
                "price": item["price"],
                "quantity": random.randint(1, 3)
            }
        })

    # 8. Někdy odebrání z košíku
    if random.random() < 0.3 and len(cart_items) > 1:
        removed_item = cart_items[0]
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Remove from Cart",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-3.5),
            "platform": platform,
            "event_properties": {
                "product_id": removed_item["id"],
                "product_name": removed_item["name"]
            }
        })
        cart_items = cart_items[1:]

    # 9. Někdy dokončení nákupu
    if random.random() < 0.6:  # 60% conversion rate
        total_amount = sum(item["price"] for item in cart_items)

        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Start Checkout",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-4),
            "platform": platform,
            "event_properties": {
                "cart_total": total_amount,
                "items_count": len(cart_items)
            }
        })

        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Complete Purchase",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-4.5),
            "platform": platform,
            "event_properties": {
                "revenue": total_amount,
                "items_count": len(cart_items),
                "payment_method": random.choice(["credit_card", "paypal", "apple_pay"]),
                "products": [{"id": item["id"], "name": item["name"], "price": item["price"]} for item in cart_items]
            },
            "revenue": total_amount  # Revenue tracking
        })

    # 10. Logout
    if random.random() < 0.7:
        events.append({
            "device_id": device_id,
            "user_id": user_id,
            "event_type": "Logout",
            "time": generate_timestamp(days_ago=base_time, hours_ago=-5),
            "platform": platform
        })

    return events


def main():
    print("🚀 Generování testovacích dat pro Amplitude...\n")

    all_events = []

    # Generujeme události pro posledních 30 dní
    for day in range(30):
        # Náhodný počet uživatelů každý den (50-200 uživatelů denně)
        daily_users_count = random.randint(50, 200)
        daily_users = random.sample(list(zip(DEVICE_IDS, USER_IDS)), daily_users_count)

        print(f"📅 Den {day+1}/30: Generuji události pro {daily_users_count} uživatelů...")

        for device_id, user_id in daily_users:
            user_events = create_user_journey(device_id, user_id, day)
            all_events.extend(user_events)

        # Někteří uživatelé se vrací vícekrát denně
        returning_users = random.sample(daily_users, min(10, len(daily_users) // 5))
        for device_id, user_id in returning_users:
            user_events = create_user_journey(device_id, user_id, day)
            all_events.extend(user_events)

    print(f"\n📊 Vygenerováno celkem {len(all_events)} událostí")
    print(f"👥 Pro {len(set(e['device_id'] for e in all_events))} unikátních uživatelů")
    print(f"💰 Celkové revenue: ${sum(e.get('revenue', 0) for e in all_events):.2f}")
    print(f"📅 Rozložených přes posledních 30 dní\n")

    # Odesíláme v dávkách po 100 událostí
    batch_size = 100
    total_batches = (len(all_events) + batch_size - 1) // batch_size

    print(f"📤 Začínám odesílat {total_batches} dávek...\n")

    for i in range(0, len(all_events), batch_size):
        batch = all_events[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"Odesílám dávku {batch_num}/{total_batches} ({len(batch)} událostí)...", end=" ")

        if not send_events(batch):
            print("❌ Chyba při odesílání, zastavuji...")
            break

        # Malá pauza mezi dávkami, aby se nešlo do rate limitu
        if batch_num < total_batches:
            time.sleep(0.5)

    print("\n✅ Hotovo! Data by měla být viditelná v Amplitude dashboard.")
    print("🔗 Přihlaš se na: https://analytics.amplitude.com/")
    print(f"\n💡 Tip: Pro ještě více dat můžeš skript spustit znovu!")


if __name__ == "__main__":
    main()
