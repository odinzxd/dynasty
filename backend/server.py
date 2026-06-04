from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import csv
import uuid
import logging
import requests
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from openpyxl import Workbook

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip()}

app = FastAPI(title="Dynasty 8 AS - Sales Management")
api_router = APIRouter(prefix="/api")

# =============== Price Matrix ===============
ZONES = ["Jessheim", "Lillestrøm", "Nedre Oslo", "Øvre Oslo", "Oslo Sentrum", "Oslo Sentralt"]
PACKAGES = ["Shell", "IPL", "MLO"]

PRICE_MATRIX = {
    "Jessheim":     {"Shell": 5000,  "IPL": 5500,  "MLO": 8000},
    "Lillestrøm":   {"Shell": 5500,  "IPL": 9000,  "MLO": 13000},
    "Nedre Oslo":   {"Shell": 7000,  "IPL": 11000, "MLO": 15000},
    "Øvre Oslo":    {"Shell": 9000,  "IPL": 15000, "MLO": 22000},
    "Oslo Sentrum": {"Shell": 12000, "IPL": 19000, "MLO": 26000},
    "Oslo Sentralt":{"Shell": 16000, "IPL": 26000, "MLO": 35000},
}

# =============== Models ===============
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: Literal["admin", "ansatt"] = "ansatt"
    employee_number: Optional[str] = None
    is_active: bool = True
    created_at: datetime

class Sale(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sale_id: str
    customer_name: str
    phone: str
    address: str
    zone: str
    package: str
    addons: List[str] = []  # ["garasje", "hage"]
    tenant_count: int = 0
    discount_type: Optional[str] = None  # "5", "10", "15", "ansatt"
    discount_percent: float = 0
    base_price: float
    total_price: float
    sale_date: str  # ISO date string
    employee_id: str
    employee_name: str
    employee_email: str
    comment: Optional[str] = None
    status: Literal["aktiv", "betalt", "kansellert", "under_behandling"] = "aktiv"
    created_at: str
    updated_at: str

class SaleCreate(BaseModel):
    customer_name: str
    phone: str
    address: str
    zone: str
    package: str
    addons: List[str] = []
    tenant_count: int = 0
    discount_type: Optional[str] = None
    sale_date: str
    comment: Optional[str] = None
    status: Literal["aktiv", "betalt", "kansellert", "under_behandling"] = "aktiv"

class SaleUpdate(BaseModel):
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    zone: Optional[str] = None
    package: Optional[str] = None
    addons: Optional[List[str]] = None
    tenant_count: Optional[int] = None
    discount_type: Optional[str] = None
    sale_date: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal["aktiv", "betalt", "kansellert", "under_behandling"]] = None


# =============== Helpers ===============
def calculate_price(zone: str, package: str, addons: List[str], tenant_count: int, discount_type: Optional[str]):
    if zone not in PRICE_MATRIX or package not in PRICE_MATRIX[zone]:
        raise HTTPException(status_code=400, detail="Ugyldig sone eller pakke")
    base = PRICE_MATRIX[zone][package]
    subtotal = float(base)
    # Addons - percentage
    if "garasje" in addons:
        subtotal += base * 0.10
    if "hage" in addons:
        subtotal += base * 0.05
    # Tenant addon - flat 500 per person
    if tenant_count and tenant_count > 0:
        subtotal += 500 * tenant_count
    # Discount
    pct = 0.0
    if discount_type == "5":
        pct = 5
    elif discount_type == "10":
        pct = 10
    elif discount_type == "15":
        pct = 15
    elif discount_type == "ansatt":
        pct = 20  # employee discount
    total = subtotal * (1 - pct / 100.0)
    return float(base), round(total, 2), pct


async def log_activity(user_id: str, user_email: str, action: str, details: Optional[dict] = None):
    await db.activity_log.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "user_email": user_email,
        "action": action,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def get_current_user(request: Request) -> User:
    # Read token from cookie or Authorization header
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    if user_doc.get("is_active", True) is False:
        # Revoke all sessions if user has been deactivated
        await db.user_sessions.delete_many({"user_id": user_doc["user_id"]})
        raise HTTPException(status_code=403, detail="Brukerkontoen er deaktivert")
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return User(**user_doc)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin tilgang kreves")
    return user


# =============== Auth Endpoints ===============
@api_router.post("/auth/session")
async def auth_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id mangler")

    # Call Emergent Auth backend to exchange session_id for session data
    r = requests.get(
        "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
        headers={"X-Session-ID": session_id},
        timeout=10,
    )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Ugyldig session_id")
    data = r.json()

    email = data["email"].lower()
    name = data.get("name", email)
    picture = data.get("picture")
    session_token = data["session_token"]

    # Find or create user
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        # Update name/picture (and ensure admin status)
        role = "admin" if email in ADMIN_EMAILS else existing.get("role", "ansatt")
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture, "role": role}}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        role = "admin" if email in ADMIN_EMAILS else "ansatt"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": role,
            "employee_number": None,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Create session record (7 days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60,
    )

    await log_activity(user_id, email, "login", {})

    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return User(**user_doc).model_dump(mode="json")


@api_router.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    return user.model_dump(mode="json")


@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if token:
        sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
        if sess:
            user_doc = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
            if user_doc:
                await log_activity(user_doc["user_id"], user_doc["email"], "logout", {})
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}


# =============== Price Matrix Endpoint ===============
@api_router.get("/price-matrix")
async def get_price_matrix():
    return {
        "zones": ZONES,
        "packages": PACKAGES,
        "matrix": PRICE_MATRIX,
        "addons": {
            "garasje": {"label": "Garasje", "type": "percent", "value": 10},
            "hage": {"label": "Hage", "type": "percent", "value": 5},
            "leietaker": {"label": "Leietakertillegg", "type": "flat", "value": 500, "per": "person"},
        },
        "discounts": [
            {"value": "5", "label": "Kunderabatt 5%"},
            {"value": "10", "label": "Kunderabatt 10%"},
            {"value": "15", "label": "Kunderabatt 15%"},
            {"value": "ansatt", "label": "Ansattrabatt 20%"},
        ],
    }


@api_router.post("/price-calculator")
async def price_calculator(body: dict):
    zone = body.get("zone")
    pkg = body.get("package")
    addons = body.get("addons", [])
    tenant_count = int(body.get("tenant_count") or 0)
    discount_type = body.get("discount_type")
    base, total, pct = calculate_price(zone, pkg, addons, tenant_count, discount_type)
    return {"base_price": base, "total_price": total, "discount_percent": pct}


# =============== Sales Endpoints ===============
@api_router.post("/sales", response_model=Sale)
async def create_sale(payload: SaleCreate, user: User = Depends(get_current_user)):
    base, total, pct = calculate_price(payload.zone, payload.package, payload.addons, payload.tenant_count, payload.discount_type)
    now = datetime.now(timezone.utc).isoformat()
    sale = {
        "sale_id": f"sale_{uuid.uuid4().hex[:12]}",
        "customer_name": payload.customer_name,
        "phone": payload.phone,
        "address": payload.address,
        "zone": payload.zone,
        "package": payload.package,
        "addons": payload.addons,
        "tenant_count": payload.tenant_count,
        "discount_type": payload.discount_type,
        "discount_percent": pct,
        "base_price": base,
        "total_price": total,
        "sale_date": payload.sale_date,
        "employee_id": user.user_id,
        "employee_name": user.name,
        "employee_email": user.email,
        "comment": payload.comment,
        "status": payload.status,
        "created_at": now,
        "updated_at": now,
    }
    await db.sales.insert_one(sale)
    await log_activity(user.user_id, user.email, "sale_created",
                       {"sale_id": sale["sale_id"], "total_price": total, "discount_percent": pct})
    return Sale(**sale)


@api_router.get("/sales", response_model=List[Sale])
async def list_sales(
    user: User = Depends(get_current_user),
    employee_id: Optional[str] = None,
    zone: Optional[str] = None,
    package: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    mine: bool = False,
):
    q = {}
    if mine or user.role != "admin":
        q["employee_id"] = user.user_id
    elif employee_id:
        q["employee_id"] = employee_id
    if zone:
        q["zone"] = zone
    if package:
        q["package"] = package
    if status:
        q["status"] = status
    if date_from or date_to:
        date_q = {}
        if date_from:
            date_q["$gte"] = date_from
        if date_to:
            date_q["$lte"] = date_to
        q["sale_date"] = date_q

    docs = await db.sales.find(q, {"_id": 0}).sort("sale_date", -1).to_list(2000)
    return [Sale(**d) for d in docs]


@api_router.get("/sales/{sale_id}", response_model=Sale)
async def get_sale(sale_id: str, user: User = Depends(get_current_user)):
    doc = await db.sales.find_one({"sale_id": sale_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Salg ikke funnet")
    if user.role != "admin" and doc["employee_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Ingen tilgang")
    return Sale(**doc)


@api_router.patch("/sales/{sale_id}", response_model=Sale)
async def update_sale(sale_id: str, payload: SaleUpdate, user: User = Depends(require_admin)):
    doc = await db.sales.find_one({"sale_id": sale_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Salg ikke funnet")

    updates = payload.model_dump(exclude_unset=True)
    merged = {**doc, **updates}
    # Recalculate price if pricing fields changed
    if any(k in updates for k in ["zone", "package", "addons", "tenant_count", "discount_type"]):
        base, total, pct = calculate_price(
            merged["zone"], merged["package"], merged.get("addons", []),
            int(merged.get("tenant_count") or 0), merged.get("discount_type")
        )
        merged["base_price"] = base
        merged["total_price"] = total
        merged["discount_percent"] = pct
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.sales.update_one({"sale_id": sale_id}, {"$set": merged})
    await log_activity(user.user_id, user.email, "sale_updated", {"sale_id": sale_id, "changes": list(updates.keys())})
    return Sale(**merged)


@api_router.delete("/sales/{sale_id}")
async def delete_sale(sale_id: str, user: User = Depends(require_admin)):
    doc = await db.sales.find_one({"sale_id": sale_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Salg ikke funnet")
    await db.sales.delete_one({"sale_id": sale_id})
    await log_activity(user.user_id, user.email, "sale_deleted", {"sale_id": sale_id})
    return {"ok": True}


# =============== Stats ===============
@api_router.get("/stats/dashboard")
async def stats_dashboard(user: User = Depends(get_current_user)):
    """Stats for current employee — today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    q = {"employee_id": user.user_id, "sale_date": today}
    docs = await db.sales.find(q, {"_id": 0}).to_list(2000)
    total_revenue = sum(d.get("total_price", 0) for d in docs if d.get("status") != "kansellert")
    count = len([d for d in docs if d.get("status") != "kansellert"])
    # Recent sales (last 5)
    recent = await db.sales.find({"employee_id": user.user_id}, {"_id": 0}).sort("created_at", -1).limit(5).to_list(5)
    return {
        "day_revenue": total_revenue,
        "day_count": count,
        "recent_sales": [Sale(**d).model_dump(mode="json") for d in recent],
    }


@api_router.get("/stats/admin")
async def stats_admin(user: User = Depends(require_admin)):
    all_docs = await db.sales.find({}, {"_id": 0}).to_list(10000)
    active = [d for d in all_docs if d.get("status") != "kansellert"]
    total_revenue = sum(d.get("total_price", 0) for d in active)
    total_count = len(active)

    # Per employee
    per_emp = {}
    for d in active:
        eid = d["employee_id"]
        if eid not in per_emp:
            per_emp[eid] = {"employee_id": eid, "employee_name": d["employee_name"], "revenue": 0, "count": 0}
        per_emp[eid]["revenue"] += d.get("total_price", 0)
        per_emp[eid]["count"] += 1

    # Per zone
    per_zone = {}
    for d in active:
        z = d["zone"]
        per_zone.setdefault(z, {"zone": z, "revenue": 0, "count": 0})
        per_zone[z]["revenue"] += d.get("total_price", 0)
        per_zone[z]["count"] += 1

    # Per day (last 30 days)
    per_day = {}
    for d in active:
        sd = d.get("sale_date", "")
        if len(sd) >= 10:
            day = sd[:10]
            per_day.setdefault(day, {"day": day, "revenue": 0, "count": 0})
            per_day[day]["revenue"] += d.get("total_price", 0)
            per_day[day]["count"] += 1

    return {
        "total_revenue": total_revenue,
        "total_count": total_count,
        "per_employee": sorted(per_emp.values(), key=lambda x: -x["revenue"]),
        "per_zone": sorted(per_zone.values(), key=lambda x: -x["revenue"]),
        "per_day": sorted(per_day.values(), key=lambda x: x["day"])[-30:],
    }


# =============== Users (admin) ===============
@api_router.get("/users", response_model=List[User])
async def list_users(user: User = Depends(require_admin)):
    docs = await db.users.find({}, {"_id": 0}).to_list(1000)
    out = []
    for d in docs:
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        out.append(User(**d))
    return out


@api_router.patch("/users/{user_id}")
async def update_user(user_id: str, body: dict, admin: User = Depends(require_admin)):
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Bruker ikke funnet")

    updates = {}
    for k in ("role", "employee_number", "name", "is_active"):
        if k in body:
            updates[k] = body[k]
    if "role" in updates and updates["role"] not in ("admin", "ansatt"):
        raise HTTPException(status_code=400, detail="Ugyldig rolle")

    # Prevent admin from demoting / deactivating themselves
    if user_id == admin.user_id:
        if updates.get("role") == "ansatt":
            raise HTTPException(status_code=400, detail="Du kan ikke fjerne din egen admin-rolle")
        if updates.get("is_active") is False:
            raise HTTPException(status_code=400, detail="Du kan ikke deaktivere din egen konto")

    if not updates:
        raise HTTPException(status_code=400, detail="Ingen felter å oppdatere")

    await db.users.update_one({"user_id": user_id}, {"$set": updates})

    # If user got deactivated, revoke all sessions immediately
    if updates.get("is_active") is False:
        await db.user_sessions.delete_many({"user_id": user_id})

    # Update employee_name on existing sales if name changed
    if "name" in updates:
        await db.sales.update_many({"employee_id": user_id}, {"$set": {"employee_name": updates["name"]}})

    await log_activity(admin.user_id, admin.email, "user_updated",
                       {"user_id": user_id, "changes": list(updates.keys())})
    return {"ok": True}


@api_router.post("/users/{user_id}/revoke-sessions")
async def revoke_user_sessions(user_id: str, admin: User = Depends(require_admin)):
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Bruker ikke funnet")
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Du kan ikke kaste ut deg selv")
    res = await db.user_sessions.delete_many({"user_id": user_id})
    await log_activity(admin.user_id, admin.email, "user_kicked",
                       {"user_id": user_id, "sessions_revoked": res.deleted_count})
    return {"ok": True, "revoked": res.deleted_count}


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(require_admin)):
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Bruker ikke funnet")
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Du kan ikke slette din egen konto")
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.users.delete_one({"user_id": user_id})
    await log_activity(admin.user_id, admin.email, "user_deleted", {"user_id": user_id, "email": target.get("email")})
    return {"ok": True}


# =============== Activity Log (admin) ===============
@api_router.get("/activity-log")
async def get_activity_log(user: User = Depends(require_admin), limit: int = 200):
    docs = await db.activity_log.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return docs


# =============== Export ===============
def _sales_rows(docs):
    headers = ["Dato", "Kunde", "Telefon", "Adresse", "Sone", "Pakke", "Tillegg",
               "Leietakere", "Rabatt %", "Grunnpris", "Totalpris", "Ansatt", "Status", "Kommentar"]
    rows = []
    for d in docs:
        rows.append([
            d.get("sale_date"),
            d.get("customer_name"),
            d.get("phone"),
            d.get("address"),
            d.get("zone"),
            d.get("package"),
            ",".join(d.get("addons", [])),
            d.get("tenant_count", 0),
            d.get("discount_percent", 0),
            d.get("base_price", 0),
            d.get("total_price", 0),
            d.get("employee_name"),
            d.get("status"),
            d.get("comment") or "",
        ])
    return headers, rows


@api_router.get("/export/csv")
async def export_csv(user: User = Depends(require_admin)):
    docs = await db.sales.find({}, {"_id": 0}).sort("sale_date", -1).to_list(10000)
    headers, rows = _sales_rows(docs)
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    await log_activity(user.user_id, user.email, "export_csv", {"count": len(rows)})
    output = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(output),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dynasty8_salg.csv"},
    )


@api_router.get("/export/xlsx")
async def export_xlsx(user: User = Depends(require_admin)):
    docs = await db.sales.find({}, {"_id": 0}).sort("sale_date", -1).to_list(10000)
    headers, rows = _sales_rows(docs)
    wb = Workbook()
    ws = wb.active
    ws.title = "Salg"
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    await log_activity(user.user_id, user.email, "export_xlsx", {"count": len(rows)})
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dynasty8_salg.xlsx"},
    )


# =============== Root ===============
@api_router.get("/")
async def root():
    return {"app": "Dynasty 8 AS", "status": "ok"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
