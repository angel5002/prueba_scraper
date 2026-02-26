from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
import json
import sys
import os
import requests
from datetime import datetime

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.falabella.com.pe/falabella-pe/category/cat40058"
N8N_WEBHOOK = os.environ.get("N8N_WEBHOOK_URL", "")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="es-PE",
        timezone_id="America/Lima",
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    stealth = Stealth()
    stealth.apply_stealth_sync(page)

    print(f"Abriendo: {URL}")
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    html = page.content()
    titulo = page.title()

    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Título de la página: {titulo}")
    print(f"Tamaño HTML: {len(html)} caracteres")
    
    browser.close()

soup = BeautifulSoup(html, "html.parser")
productos = []
for pod in soup.select("a[data-pod='catalyst-pod']"):
    producto_id = pod.get("data-key", "")
    url_producto = "https://www.falabella.com.pe" + pod.get("href", "")
    marca = pod.select_one("b.pod-title")
    nombre = pod.select_one("b.pod-subTitle")
    vendedor = pod.select_one("b.pod-sellerText")
    precio_actual_el = pod.select_one("li.prices-0")
    precio_normal_el = pod.select_one("li.prices-1")
    precio_actual = None
    if precio_actual_el:
        precio_actual = (
            precio_actual_el.get("data-internet-price") or
            precio_actual_el.get("data-event-price")
        )
    precio_normal = precio_normal_el.get("data-normal-price") if precio_normal_el else None
    rating_el = pod.select_one("div[data-rating]")
    reviews_el = pod.select_one("span[data-rating]")
    descuento_el = pod.select_one("li.prices-0 span.discount-badge-item")
    productos.append({
        "id": producto_id,
        "marca": marca.text.strip() if marca else None,
        "nombre": nombre.text.strip() if nombre else None,
        "vendedor": vendedor.text.strip().replace("Por ", "") if vendedor else None,
        "precio_actual": precio_actual,
        "precio_normal": precio_normal,
        "descuento": descuento_el.text.strip() if descuento_el else None,
        "rating": rating_el.get("data-rating") if rating_el else None,
        "reviews": reviews_el.get("data-rating") if reviews_el else None,
        "url": url_producto,
    })

resultado = {
    "fecha": datetime.now().isoformat(),
    "total": len(productos),
    "productos": productos
}

print(f"✓ {len(productos)} productos encontrados")
print(f"Título: {titulo}")

# Enviar a n8n
if N8N_WEBHOOK:
    try:
        r = requests.post(N8N_WEBHOOK, json=resultado, timeout=30)
        print(f"✓ Enviado a n8n: {r.status_code}")
    except Exception as e:
        print(f"Error enviando a n8n: {e}")

# Guardar localmente también
with open("productos.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)
print("✓ JSON guardado: productos.json")
