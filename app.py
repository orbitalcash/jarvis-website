"""
JARVIS AI — Site web public premium
Vitrine + vente des créations numériques
Port : 8080
Auto-update : fetch Gumroad API directement (GUMROAD_TOKEN env var)
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

HERE          = Path(__file__).parent
DATA_DIR      = Path(r"C:\Users\Bad\JARVIS\data")
CREATIONS_IDX = DATA_DIR / "creations_index.json"
PRODUCTS_JSON = HERE / "products.json"
STATIC_DIR    = HERE / "static"
TMPL_DIR      = HERE / "templates"

app       = FastAPI(title="JARVIS AI")
templates = Jinja2Templates(directory=str(TMPL_DIR))

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Cache Gumroad pour éviter trop de requêtes API
_gumroad_cache: dict = {"products": [], "fetched_at": 0}
CACHE_TTL = 300  # 5 minutes


async def fetch_gumroad_products() -> list:
    """Récupère tous les produits publiés depuis l'API Gumroad."""
    token = os.environ.get("GUMROAD_TOKEN", "")
    if not token:
        return []
    try:
        import httpx
        all_prods = []
        params = {"access_token": token}
        async with httpx.AsyncClient(timeout=10) as c:
            while True:
                r = await c.get("https://api.gumroad.com/v2/products", params=params)
                data = r.json()
                all_prods.extend(data.get("products", []))
                nk = data.get("next_page_key")
                if not nk:
                    break
                params = {"access_token": token, "page_key": nk}
        return [p for p in all_prods if p.get("published")]
    except Exception:
        return []


def gumroad_to_product(p: dict) -> dict:
    """Convertit un produit Gumroad en format vitrine."""
    name = p.get("name", "")
    # Détecter le type depuis le nom
    ptype = "ebook"
    name_l = name.lower()
    if "n8n" in name_l or "workflow" in name_l:  ptype = "n8n_workflow"
    elif "script" in name_l or "python" in name_l: ptype = "python_script"
    elif "saas" in name_l or "fastapi" in name_l:  ptype = "micro_saas"
    elif "prompt" in name_l:                        ptype = "prompt_pack"
    elif "guide" in name_l or "staking" in name_l: ptype = "article"
    elif "bot" in name_l or "crypto" in name_l:    ptype = "python_script"

    return {
        "id":          p.get("id", ""),
        "type":        ptype,
        "topic":       name,
        "title":       name,
        "description": p.get("description", "")[:200],
        "price_eur":   p.get("price", 0) / 100,
        "gumroad_url": p.get("short_url", ""),
        "published":   True,
        "tags":        ["ia", "digital", "premium"],
    }


async def load_products() -> list:
    global _gumroad_cache
    now = time.time()

    # 1. Cache frais → retourner directement
    if _gumroad_cache["products"] and (now - _gumroad_cache["fetched_at"]) < CACHE_TTL:
        return _gumroad_cache["products"]

    # 2. API Gumroad (prod Railway)
    gumroad_token = os.environ.get("GUMROAD_TOKEN", "")
    if gumroad_token:
        prods = await fetch_gumroad_products()
        if prods:
            converted = [gumroad_to_product(p) for p in prods]
            _gumroad_cache = {"products": converted, "fetched_at": now}
            return converted

    # 3. Fallback local (dev Windows)
    if CREATIONS_IDX.exists():
        try:
            idx = json.loads(CREATIONS_IDX.read_text("utf-8"))
            return [p for p in idx if p.get("published") and (p.get("gumroad_url") or p.get("publish_url"))]
        except Exception:
            pass

    # 4. Fallback products.json embarqué
    if PRODUCTS_JSON.exists():
        try:
            return json.loads(PRODUCTS_JSON.read_text("utf-8"))
        except Exception:
            pass

    return []


def enrich(p: dict) -> dict:
    """Normalise et enrichit un produit pour l'affichage."""
    url = p.get("gumroad_url") or p.get("publish_url", "https://ngombad.gumroad.com")
    price_raw = p.get("price_eur") or p.get("price", "9€")
    try:
        price = float(str(price_raw).replace("€","").replace("/mois","").split("–")[0].strip())
    except Exception:
        price = 9.0

    icons = {
        "ebook":        "📘", "prompt_pack": "✨", "python_script": "🐍",
        "article":      "📝", "n8n_workflow": "⚙️", "micro_saas": "🚀",
        "emergent_app": "📱", "cheatsheet": "📋",
    }
    labels = {
        "ebook":        "eBook Premium",  "prompt_pack":  "Pack Prompts IA",
        "python_script":"Script Python",  "article":      "Guide Complet",
        "n8n_workflow": "Workflow n8n",   "micro_saas":   "Template SaaS",
        "emergent_app": "App No-Code",    "cheatsheet":   "Cheat Sheet",
    }
    ctype = p.get("type","ebook")
    return {**p,
        "url":       url,
        "price":     price,
        "icon":      icons.get(ctype, "💡"),
        "type_label":labels.get(ctype, "Produit Digital"),
        "slug":      url.split("/")[-1],
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    products = [enrich(p) for p in await load_products()]
    stats = {
        "total":    len(products),
        "types":    len({p["type"] for p in products}),
        "min_price": min((p["price"] for p in products), default=9),
    }
    return templates.TemplateResponse(request, "index.html", {
        "products": products[:6], "stats": stats,
        "year": datetime.now().year,
    })


@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request, type: str = "", q: str = ""):
    raw = await load_products()
    all_p = [enrich(p) for p in raw]
    if type:
        all_p = [p for p in all_p if p.get("type") == type]
    if q:
        all_p = [p for p in all_p if q.lower() in p.get("topic","").lower()]
    types  = list({p["type"]: p["type_label"] for p in [enrich(x) for x in raw]}.items())
    return templates.TemplateResponse(request, "products.html", {
        "products": all_p, "types": types,
        "filter_type": type, "query": q,
        "year": datetime.now().year,
    })


@app.get("/api/products")
async def api_products():
    return [enrich(p) for p in await load_products()]


@app.get("/health")
async def health():
    prods = await load_products()
    return {"status": "ok", "products": len(prods)}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
