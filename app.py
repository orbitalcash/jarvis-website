"""
JARVIS AI — Site web public premium
Vitrine + vente des créations numériques
Port : 8080
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Chemin local Windows (dev) ou fichier embarqué (prod Railway/Render)
HERE          = Path(__file__).parent
DATA_DIR      = Path(r"C:\Users\Bad\JARVIS\data")
CREATIONS_IDX = DATA_DIR / "creations_index.json"
PRODUCTS_JSON = HERE / "products.json"          # copie embarquée pour prod
STATIC_DIR    = HERE / "static"
TMPL_DIR      = HERE / "templates"

app       = FastAPI(title="JARVIS AI")
templates = Jinja2Templates(directory=str(TMPL_DIR))

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def load_products():
    # 1. Essai fichier local JARVIS (dev Windows)
    if CREATIONS_IDX.exists():
        try:
            idx = json.loads(CREATIONS_IDX.read_text("utf-8"))
            return [p for p in idx if p.get("published") and (p.get("gumroad_url") or p.get("publish_url"))]
        except Exception:
            pass
    # 2. Fallback : produits embarqués (prod Railway/Render)
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
    products = [enrich(p) for p in load_products()]
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
    all_p = [enrich(p) for p in load_products()]
    if type:
        all_p = [p for p in all_p if p.get("type") == type]
    if q:
        all_p = [p for p in all_p if q.lower() in p.get("topic","").lower()]
    types  = list({p["type"]: p["type_label"] for p in [enrich(x) for x in load_products()]}.items())
    return templates.TemplateResponse(request, "products.html", {
        "products": all_p, "types": types,
        "filter_type": type, "query": q,
        "year": datetime.now().year,
    })


@app.get("/api/products")
async def api_products():
    return [enrich(p) for p in load_products()]


@app.get("/health")
async def health():
    return {"status": "ok", "products": len(load_products())}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
