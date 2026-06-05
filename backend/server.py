from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import io
import csv
import uuid
import logging
import sqlite3
import json
import threading
from pathlib import Path
from passlib.context import CryptContext
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from openpyxl import Workbook

ROOT_DIR = Path(__file__).parent
FRONTEND_BUILD_DIR = ROOT_DIR.parent / "frontend" / "build"
load_dotenv(ROOT_DIR / '.env')


def _resolve_database_path() -> Path:
    database_path = os.environ.get("DATABASE_PATH")
    if database_path:
        return Path(database_path)

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("sqlite:///"):
            return Path(database_url.replace("sqlite:///", ""))
        return Path(database_url)

    persistent_dir = Path("/data")
    if persistent_dir.exists():
        return persistent_dir / "database.sqlite"

    return ROOT_DIR / "database.sqlite"


DATABASE_PATH = _resolve_database_path()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_ADMIN_EMAILS = {"odinzyt@gmail.com"}
DEFAULT_ADMIN_USERNAME = os.environ.get("INITIAL_ADMIN_USERNAME", "odin").strip().lower()
DEFAULT_ADMIN_PASSWORD = os.environ.get("INITIAL_ADMIN_PASSWORD", "").strip()
ADMIN_EMAILS = DEFAULT_ADMIN_EMAILS | {
    e.strip().lower()
    for e in os.environ.get('ADMIN_EMAILS', '').split(',')
    if e.strip()
}

_db_lock = threading.Lock()
_db_connection = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
_db_connection.row_factory = sqlite3.Row
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _execute(sql: str, params=(), commit: bool = False):
    with _db_lock:
        cur = _db_connection.cursor()
        cur.execute(sql, params)
        if commit:
            _db_connection.commit()
        return cur


def _column_exists(table_name: str, column_name: str) -> bool:
    cur = _execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cur.fetchall())


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, password_hash: Optional[str]) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(password, password_hash)


def _ensure_initial_admin():
    if not DEFAULT_ADMIN_PASSWORD:
        return

    email = "odinzyt@gmail.com"
    now = datetime.now(timezone.utc).isoformat()
    password_hash = _hash_password(DEFAULT_ADMIN_PASSWORD)
    existing = _execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if existing:
        next_username = existing["username"] or DEFAULT_ADMIN_USERNAME
        next_password_hash = existing["password_hash"] or password_hash
        _execute(
            "UPDATE users SET username = ?, password_hash = ?, role = ?, is_active = ? WHERE user_id = ?",
            (next_username, next_password_hash, "admin", 1, existing["user_id"]),
            commit=True,
        )
        return

    _execute(
        "INSERT INTO users (user_id, username, email, name, picture, role, employee_number, password_hash, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            f"user_{uuid.uuid4().hex[:12]}",
            DEFAULT_ADMIN_USERNAME,
            email,
            "Odin",
            None,
            "admin",
            None,
            password_hash,
            1,
            now,
        ),
        commit=True,
    )


def _ensure_default_products():
    existing = _execute("SELECT COUNT(*) AS count FROM sale_products").fetchone()
    if existing and existing["count"] > 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    defaults = [
        ("Shell", "Shell Standard", 5000),
        ("Shell", "Shell Premium", 9000),
        ("IPL", "IPL Standard", 11000),
        ("IPL", "IPL Premium", 19000),
        ("MLO", "MLO Standard", 15000),
        ("MLO", "MLO Premium", 26000),
    ]
    for category, name, price in defaults:
        _execute(
            "INSERT INTO sale_products (product_id, category, name, price_per_day, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"product_{uuid.uuid4().hex[:12]}", category, name, price, 1, now, now),
            commit=True,
        )


async def _fetch_one(sql: str, params=()):
    cur = await run_in_threadpool(_execute, sql, params, False)
    return cur.fetchone()


async def _fetch_all(sql: str, params=()):
    cur = await run_in_threadpool(_execute, sql, params, False)
    return cur.fetchall()


async def _execute_commit(sql: str, params=()):
    await run_in_threadpool(_execute, sql, params, True)


def _json_dump(value):
    return json.dumps(value or [], ensure_ascii=False)


def _json_load(value):
    if value is None or value == '':
        return []
    return json.loads(value)


def _row_to_user(row):
    if row is None:
        return None
    data = dict(row)
    data['is_active'] = bool(data.get('is_active', 1))
    return data


def _row_to_sale(row):
    if row is None:
        return None
    data = dict(row)
    data['addons'] = _json_load(data.get('addons'))
    return data


def _row_to_activity(row):
    if row is None:
        return None
    data = dict(row)
    details = data.get('details')
    data['details'] = json.loads(details) if details else {}
    return data


def _row_to_product(row):
    if row is None:
        return None
    data = dict(row)
    data["is_active"] = bool(data.get("is_active", 1))
    return data


def _init_db():
    _execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            picture TEXT,
            role TEXT NOT NULL DEFAULT 'ansatt',
            employee_number TEXT,
            password_hash TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    ''', commit=True)
    if not _column_exists("users", "username"):
        _execute("ALTER TABLE users ADD COLUMN username TEXT", commit=True)
    if not _column_exists("users", "password_hash"):
        _execute("ALTER TABLE users ADD COLUMN password_hash TEXT", commit=True)
    _execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''', commit=True)
    _execute('''
        CREATE TABLE IF NOT EXISTS sales (
            sale_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            zone TEXT NOT NULL,
            package TEXT NOT NULL,
            addons TEXT NOT NULL,
            tenant_count INTEGER NOT NULL,
            discount_type TEXT,
            discount_percent REAL NOT NULL,
            base_price REAL NOT NULL,
            total_price REAL NOT NULL,
            sale_date TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            employee_email TEXT NOT NULL,
            comment TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''', commit=True)
    if not _column_exists("sales", "product_id"):
        _execute("ALTER TABLE sales ADD COLUMN product_id TEXT", commit=True)
    _execute('''
        CREATE TABLE IF NOT EXISTS sale_products (
            product_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price_per_day REAL NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''', commit=True)
    _execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            log_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            user_email TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)', commit=True)
    _execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sales_employee_id ON sales(employee_id)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sales_sale_date ON sales(sale_date)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales(product_id)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sale_products_category ON sale_products(category)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp)', commit=True)
    _ensure_initial_admin()
    _ensure_default_products()


_init_db()

app = FastAPI(title="Dynasty 8 AS - Sales Management")
api_router = APIRouter(prefix="/api")

# =============== Price Matrix ===============
ZONES = ["Jessheim", "Lillestr├©m", "Nedre Oslo", "├ÿvre Oslo", "Oslo Sentrum", "Oslo Sentralt"]
PACKAGES = ["Shell", "IPL", "MLO"]

PRICE_MATRIX = {
    "Jessheim":     {"Shell": 5000,  "IPL": 5500,  "MLO": 8000},
    "Lillestr├©m":   {"Shell": 5500,  "IPL": 9000,  "MLO": 13000},
    "Nedre Oslo":   {"Shell": 7000,  "IPL": 11000, "MLO": 15000},
    "├ÿvre Oslo":    {"Shell": 9000,  "IPL": 15000,  "MLO": 22000},
    "Oslo Sentrum": {"Shell": 12000, "IPL": 19000, "MLO": 26000},
    "Oslo Sentralt":{"Shell": 16000, "IPL": 26000, "MLO": 35000},
}

# =============== Models ===============
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    username: Optional[str] = None
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
    product_id: Optional[str] = None
    package: str
    addons: List[str] = []
    tenant_count: int = 0
    discount_type: Optional[str] = None
    discount_percent: float = 0
    base_price: float
    total_price: float
    sale_date: str
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
    product_id: Optional[str] = None
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
    product_id: Optional[str] = None
    package: Optional[str] = None
    addons: Optional[List[str]] = None
    tenant_count: Optional[int] = None
    discount_type: Optional[str] = None
    sale_date: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[Literal["aktiv", "betalt", "kansellert", "under_behandling"]] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    name: str
    role: Literal["admin", "ansatt"] = "ansatt"
    employee_number: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    password: str


class SaleProduct(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_id: str
    category: Literal["Shell", "IPL", "MLO"]
    name: str
    price_per_day: float
    is_active: bool = True
    created_at: str
    updated_at: str


class SaleProductCreate(BaseModel):
    category: Literal["Shell", "IPL", "MLO"]
    name: str
    price_per_day: float
    is_active: bool = True


class SaleProductUpdate(BaseModel):
    category: Optional[Literal["Shell", "IPL", "MLO"]] = None
    name: Optional[str] = None
    price_per_day: Optional[float] = None
    is_active: Optional[bool] = None


# =============== Helpers ===============
async def _get_product(product_id_or_name: Optional[str], include_inactive: bool = False):
    if not product_id_or_name:
        return None
    normalized = product_id_or_name.strip()
    if " - " in normalized:
        normalized = normalized.split(" - ", 1)[1].strip()
    if include_inactive:
        return await _fetch_one(
            "SELECT * FROM sale_products WHERE product_id = ? OR name = ? OR category = ? ORDER BY category, name LIMIT 1",
            (product_id_or_name, normalized, normalized),
        )
    return await _fetch_one(
        "SELECT * FROM sale_products WHERE (product_id = ? OR name = ? OR category = ?) AND is_active = 1 ORDER BY category, name LIMIT 1",
        (product_id_or_name, normalized, normalized),
    )


async def calculate_price(product_id_or_name: str, addons: List[str], tenant_count: int, discount_type: Optional[str]):
    product = await _get_product(product_id_or_name)
    if not product:
        raise HTTPException(status_code=400, detail="Ugyldig eller deaktivert boligtype")
    base = float(product["price_per_day"])
    subtotal = float(base)
    if "garasje" in addons:
        subtotal += base * 0.10
    if "hage" in addons:
        subtotal += base * 0.05
    if tenant_count and tenant_count > 0:
        subtotal += 500 * tenant_count
    pct = 0.0
    if discount_type == "5":
        pct = 5
    elif discount_type == "10":
        pct = 10
    elif discount_type == "15":
        pct = 15
    elif discount_type == "ansatt":
        pct = 20
    total = subtotal * (1 - pct / 100.0)
    return float(base), round(total, 2), pct, _row_to_product(product)


async def log_activity(user_id: str, user_email: str, action: str, details: Optional[dict] = None):
    await _execute_commit(
        "INSERT OR REPLACE INTO activity_log (log_id, user_id, user_email, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (
            f"log_{uuid.uuid4().hex[:12]}",
            user_id,
            user_email,
            action,
            json.dumps(details or {}, ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


async def get_current_user(request: Request) -> User:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await _fetch_one("SELECT * FROM user_sessions WHERE session_token = ?", (token,))
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (session_doc["user_id"],))
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    user_data = _row_to_user(user_doc)
    if user_data["email"].lower() in ADMIN_EMAILS and user_data["role"] != "admin":
        await _execute_commit("UPDATE users SET role = ? WHERE user_id = ?", ("admin", user_data["user_id"]))
        user_data["role"] = "admin"
    if not bool(user_data["is_active"]):
        await _execute_commit("DELETE FROM user_sessions WHERE user_id = ?", (user_data["user_id"],))
        raise HTTPException(status_code=403, detail="Brukerkontoen er deaktivert")
    return User(**user_data)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin tilgang kreves")
    return user


# =============== Auth Endpoints ===============
@api_router.post("/auth/login")
async def auth_login(payload: LoginRequest, response: Response):
    identifier = payload.username.strip().lower()
    if not identifier or not payload.password:
        raise HTTPException(status_code=400, detail="Brukernavn og passord kreves")

    user_doc = await _fetch_one(
        "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
        (identifier, identifier),
    )
    if not user_doc or not _verify_password(payload.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Ugyldig brukernavn eller passord")
    if not bool(user_doc["is_active"]):
        raise HTTPException(status_code=403, detail="Brukerkontoen er deaktivert")

    user_id = user_doc["user_id"]
    email = user_doc["email"]
    session_token = f"session_{uuid.uuid4().hex}{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await _execute_commit(
        "INSERT OR REPLACE INTO user_sessions (session_token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (session_token, user_id, expires_at.isoformat(), datetime.now(timezone.utc).isoformat()),
    )

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

    user_doc = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return User(**_row_to_user(user_doc)).model_dump(mode="json")


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
        sess = await _fetch_one("SELECT * FROM user_sessions WHERE session_token = ?", (token,))
        if sess:
            user_doc = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (sess["user_id"],))
            if user_doc:
                await log_activity(user_doc["user_id"], user_doc["email"], "logout", {})
        await _execute_commit("DELETE FROM user_sessions WHERE session_token = ?", (token,))
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}


# =============== Price Matrix Endpoint ===============
@api_router.get("/price-matrix")
async def get_price_matrix():
    products = [_row_to_product(row) for row in await _fetch_all("SELECT * FROM sale_products ORDER BY category, name", ())]
    active_products = [p for p in products if p["is_active"]]
    return {
        "zones": ZONES,
        "packages": PACKAGES,
        "matrix": PRICE_MATRIX,
        "product_categories": ["Shell", "IPL", "MLO"],
        "products": products,
        "active_products": active_products,
        "addons": {
            "garasje": {"label": "Garasje", "type": "percent", "value": 10},
            "hage": {"label": "Hage", "type": "percent", "value": 5},
            "leietaker": {"label": "Leietakertillegg", "type": "flat", "value": 500, "per": "person"},
        },
        "discounts": [
            {"value": "5", "label": "Kunderabatt 5%"},
            {"value": "10", "label": "Kunderabatt 10%"},
            {"value": "15", "label": "Kunderabatt 15%"},
            {"value": "ansatt", "label": "Ansattrabatt"},
        ],
    }


@api_router.post("/price-calculator")
async def price_calculator(body: dict):
    product_id = body.get("product_id") or body.get("package")
    addons = body.get("addons", [])
    tenant_count = int(body.get("tenant_count") or 0)
    discount_type = body.get("discount_type")
    base, total, pct, product = await calculate_price(product_id, addons, tenant_count, discount_type)
    return {"base_price": base, "total_price": total, "discount_percent": pct, "product": product}


# =============== Sales Endpoints ===============
@api_router.post("/sales", response_model=Sale)
async def create_sale(payload: SaleCreate, user: User = Depends(get_current_user)):
    product_key = payload.product_id or payload.package
    base, total, pct, product = await calculate_price(product_key, payload.addons, payload.tenant_count, payload.discount_type)
    now = datetime.now(timezone.utc).isoformat()
    sale = {
        "sale_id": f"sale_{uuid.uuid4().hex[:12]}",
        "customer_name": payload.customer_name,
        "phone": payload.phone,
        "address": payload.address,
        "zone": payload.zone,
        "product_id": product["product_id"],
        "package": f'{product["category"]} - {product["name"]}',
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
    await _execute_commit(
        "INSERT INTO sales (sale_id, customer_name, phone, address, zone, product_id, package, addons, tenant_count, discount_type, discount_percent, base_price, total_price, sale_date, employee_id, employee_name, employee_email, comment, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sale["sale_id"], sale["customer_name"], sale["phone"], sale["address"], sale["zone"], sale["product_id"], sale["package"], _json_dump(sale["addons"]), sale["tenant_count"], sale["discount_type"], sale["discount_percent"], sale["base_price"], sale["total_price"], sale["sale_date"], sale["employee_id"], sale["employee_name"], sale["employee_email"], sale["comment"], sale["status"], sale["created_at"], sale["updated_at"],
        ),
    )
    await log_activity(user.user_id, user.email, "sale_created",
                       {"sale_id": sale["sale_id"], "total_price": total, "discount_percent": pct})
    return Sale(**sale)


async def _sales_query(where_clause: str = "", params=()):
    sql = "SELECT * FROM sales"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += " ORDER BY sale_date DESC LIMIT 2000"
    rows = await _fetch_all(sql, params)
    return [_row_to_sale(row) for row in rows]


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
    filters = []
    params = []
    if mine or user.role != "admin":
        filters.append("employee_id = ?")
        params.append(user.user_id)
    elif employee_id:
        filters.append("employee_id = ?")
        params.append(employee_id)
    if zone:
        filters.append("zone = ?")
        params.append(zone)
    if package:
        filters.append("package = ?")
        params.append(package)
    if status:
        filters.append("status = ?")
        params.append(status)
    if date_from:
        filters.append("sale_date >= ?")
        params.append(date_from)
    if date_to:
        filters.append("sale_date <= ?")
        params.append(date_to)

    where_clause = " AND ".join(filters)
    return [Sale(**sale) for sale in await _sales_query(where_clause, tuple(params))]


@api_router.get("/sales/{sale_id}", response_model=Sale)
async def get_sale(sale_id: str, user: User = Depends(get_current_user)):
    doc = await _fetch_one("SELECT * FROM sales WHERE sale_id = ?", (sale_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="Salg ikke funnet")
    sale = _row_to_sale(doc)
    if user.role != "admin" and sale["employee_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Ingen tilgang")
    return Sale(**sale)


@api_router.patch("/sales/{sale_id}", response_model=Sale)
async def update_sale(sale_id: str, payload: SaleUpdate, user: User = Depends(require_admin)):
    doc = await _fetch_one("SELECT * FROM sales WHERE sale_id = ?", (sale_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="Salg ikke funnet")

    existing = _row_to_sale(doc)
    updates = payload.model_dump(exclude_unset=True)
    merged = {**existing, **updates}
    if any(k in updates for k in ["product_id", "package", "addons", "tenant_count", "discount_type"]):
        product_key = merged.get("product_id") or merged.get("package")
        base, total, pct, product = await calculate_price(
            product_key, merged.get("addons", []),
            int(merged.get("tenant_count") or 0), merged.get("discount_type"),
        )
        merged["product_id"] = product["product_id"]
        merged["package"] = f'{product["category"]} - {product["name"]}'
        merged["base_price"] = base
        merged["total_price"] = total
        merged["discount_percent"] = pct
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()

    fields = []
    params = []
    for key, value in merged.items():
        if key == "sale_id":
            continue
        if key == "addons":
            value = _json_dump(value)
        fields.append(f"{key} = ?")
        params.append(value)
    params.append(sale_id)
    await _execute_commit(f"UPDATE sales SET {', '.join(fields)} WHERE sale_id = ?", tuple(params))
    await log_activity(user.user_id, user.email, "sale_updated", {"sale_id": sale_id, "changes": list(updates.keys())})
    return Sale(**merged)


@api_router.delete("/sales/{sale_id}")
async def delete_sale(sale_id: str, user: User = Depends(require_admin)):
    doc = await _fetch_one("SELECT * FROM sales WHERE sale_id = ?", (sale_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="Salg ikke funnet")
    await _execute_commit("DELETE FROM sales WHERE sale_id = ?", (sale_id,))
    await log_activity(user.user_id, user.email, "sale_deleted", {"sale_id": sale_id})
    return {"ok": True}


# =============== Stats ===============
@api_router.get("/stats/dashboard")
async def stats_dashboard(user: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    docs = await _fetch_all("SELECT * FROM sales WHERE employee_id = ? AND sale_date = ? ORDER BY created_at DESC", (user.user_id, today))
    sales = [_row_to_sale(row) for row in docs]
    total_revenue = sum(d.get("total_price", 0) for d in sales if d.get("status") != "kansellert")
    count = len([d for d in sales if d.get("status") != "kansellert"])
    recent_rows = await _fetch_all("SELECT * FROM sales WHERE employee_id = ? ORDER BY created_at DESC LIMIT 5", (user.user_id,))
    return {
        "day_revenue": total_revenue,
        "day_count": count,
        "recent_sales": [Sale(**_row_to_sale(row)).model_dump(mode="json") for row in recent_rows],
    }


@api_router.get("/stats/admin")
async def stats_admin(user: User = Depends(require_admin)):
    docs = await _fetch_all("SELECT * FROM sales ORDER BY sale_date DESC", ())
    sales = [_row_to_sale(row) for row in docs]
    active = [d for d in sales if d.get("status") != "kansellert"]
    total_revenue = sum(d.get("total_price", 0) for d in active)
    per_emp = {}
    for d in active:
        eid = d["employee_id"]
        if eid not in per_emp:
            per_emp[eid] = {"employee_id": eid, "employee_name": d["employee_name"], "revenue": 0, "count": 0}
        per_emp[eid]["revenue"] += d.get("total_price", 0)
        per_emp[eid]["count"] += 1
    per_zone = {}
    for d in active:
        z = d["zone"]
        per_zone.setdefault(z, {"zone": z, "revenue": 0, "count": 0})
        per_zone[z]["revenue"] += d.get("total_price", 0)
        per_zone[z]["count"] += 1
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
        "total_count": len(active),
        "per_employee": sorted(per_emp.values(), key=lambda x: -x["revenue"]),
        "per_zone": sorted(per_zone.values(), key=lambda x: -x["revenue"]),
        "per_day": sorted(per_day.values(), key=lambda x: x["day"])[-30:],
    }


@api_router.get("/system/database")
async def database_status(user: User = Depends(require_admin)):
    try:
        row = await _fetch_one("SELECT 1 AS ok", ())
        return {
            "ok": bool(row and row["ok"] == 1),
            "database_path": str(DATABASE_PATH),
            "persistent_storage": str(DATABASE_PATH).startswith("/data/"),
            "error": None,
        }
    except Exception as exc:
        logger.exception("Database health check failed")
        return {
            "ok": False,
            "database_path": str(DATABASE_PATH),
            "persistent_storage": str(DATABASE_PATH).startswith("/data/"),
            "error": str(exc),
        }


@api_router.get("/products", response_model=List[SaleProduct])
async def list_products(user: User = Depends(require_admin)):
    rows = await _fetch_all("SELECT * FROM sale_products ORDER BY category, name", ())
    return [SaleProduct(**_row_to_product(row)) for row in rows]


@api_router.post("/products", response_model=SaleProduct)
async def create_product(payload: SaleProductCreate, user: User = Depends(require_admin)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Navn mangler")
    if payload.price_per_day <= 0:
        raise HTTPException(status_code=400, detail="Pris per dag må være større enn 0")

    now = datetime.now(timezone.utc).isoformat()
    product_id = f"product_{uuid.uuid4().hex[:12]}"
    await _execute_commit(
        "INSERT INTO sale_products (product_id, category, name, price_per_day, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (product_id, payload.category, name, float(payload.price_per_day), 1 if payload.is_active else 0, now, now),
    )
    await log_activity(user.user_id, user.email, "product_created", {"product_id": product_id, "category": payload.category, "name": name})
    row = await _fetch_one("SELECT * FROM sale_products WHERE product_id = ?", (product_id,))
    return SaleProduct(**_row_to_product(row))


@api_router.patch("/products/{product_id}", response_model=SaleProduct)
async def update_product(product_id: str, payload: SaleProductUpdate, user: User = Depends(require_admin)):
    existing = await _fetch_one("SELECT * FROM sale_products WHERE product_id = ?", (product_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Boligtype ikke funnet")

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["name"] = updates["name"].strip()
        if not updates["name"]:
            raise HTTPException(status_code=400, detail="Navn mangler")
    if "price_per_day" in updates and updates["price_per_day"] <= 0:
        raise HTTPException(status_code=400, detail="Pris per dag må være større enn 0")
    if "is_active" in updates:
        updates["is_active"] = 1 if updates["is_active"] else 0
    if not updates:
        raise HTTPException(status_code=400, detail="Ingen felter å oppdatere")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    for key, value in updates.items():
        fields.append(f"{key} = ?")
        params.append(value)
    params.append(product_id)
    await _execute_commit(f"UPDATE sale_products SET {', '.join(fields)} WHERE product_id = ?", tuple(params))
    await log_activity(user.user_id, user.email, "product_updated", {"product_id": product_id, "changes": list(updates.keys())})
    row = await _fetch_one("SELECT * FROM sale_products WHERE product_id = ?", (product_id,))
    return SaleProduct(**_row_to_product(row))


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: User = Depends(require_admin)):
    existing = await _fetch_one("SELECT * FROM sale_products WHERE product_id = ?", (product_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Boligtype ikke funnet")

    used = await _fetch_one("SELECT COUNT(*) AS count FROM sales WHERE product_id = ?", (product_id,))
    if used and used["count"] > 0:
        await _execute_commit("UPDATE sale_products SET is_active = 0, updated_at = ? WHERE product_id = ?", (datetime.now(timezone.utc).isoformat(), product_id))
        await log_activity(user.user_id, user.email, "product_deactivated", {"product_id": product_id, "reason": "used_in_sales"})
        return {"ok": True, "deactivated": True}

    await _execute_commit("DELETE FROM sale_products WHERE product_id = ?", (product_id,))
    await log_activity(user.user_id, user.email, "product_deleted", {"product_id": product_id})
    return {"ok": True, "deleted": True}


# =============== Users (admin) ===============
@api_router.get("/users", response_model=List[User])
async def list_users(user: User = Depends(require_admin)):
    rows = await _fetch_all("SELECT * FROM users ORDER BY created_at DESC", ())
    return [User(**_row_to_user(row)) for row in rows]


@api_router.post("/users", response_model=User)
async def create_user(payload: UserCreate, admin: User = Depends(require_admin)):
    username = payload.username.strip().lower()
    email = payload.email.strip().lower()
    name = payload.name.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Brukernavn må ha minst 3 tegn")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Passord må ha minst 8 tegn")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Ugyldig e-post")
    if not name:
        raise HTTPException(status_code=400, detail="Navn mangler")

    existing = await _fetch_one("SELECT user_id FROM users WHERE lower(username) = ? OR lower(email) = ?", (username, email))
    if existing:
        raise HTTPException(status_code=400, detail="Brukernavn eller e-post er allerede i bruk")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    await _execute_commit(
        "INSERT INTO users (user_id, username, email, name, picture, role, employee_number, password_hash, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            username,
            email,
            name,
            None,
            payload.role,
            payload.employee_number,
            _hash_password(payload.password),
            1,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    await log_activity(admin.user_id, admin.email, "user_created", {"user_id": user_id, "email": email, "role": payload.role})
    user_doc = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return User(**_row_to_user(user_doc))


@api_router.patch("/users/{user_id}")
async def update_user(user_id: str, body: dict, admin: User = Depends(require_admin)):
    target = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Bruker ikke funnet")

    updates = {}
    for k in ("role", "employee_number", "name", "is_active", "username", "email"):
        if k in body:
            updates[k] = body[k]
    if "username" in updates:
        updates["username"] = updates["username"].strip().lower() if updates["username"] else None
        if not updates["username"] or len(updates["username"]) < 3:
            raise HTTPException(status_code=400, detail="Brukernavn må ha minst 3 tegn")
        duplicate = await _fetch_one("SELECT user_id FROM users WHERE lower(username) = ? AND user_id != ?", (updates["username"], user_id))
        if duplicate:
            raise HTTPException(status_code=400, detail="Brukernavnet er allerede i bruk")
    if "email" in updates:
        updates["email"] = updates["email"].strip().lower() if updates["email"] else None
        if not updates["email"] or "@" not in updates["email"]:
            raise HTTPException(status_code=400, detail="Ugyldig e-post")
        duplicate = await _fetch_one("SELECT user_id FROM users WHERE lower(email) = ? AND user_id != ?", (updates["email"], user_id))
        if duplicate:
            raise HTTPException(status_code=400, detail="E-posten er allerede i bruk")
    if "role" in updates and updates["role"] not in ("admin", "ansatt"):
        raise HTTPException(status_code=400, detail="Ugyldig rolle")
    if user_id == admin.user_id:
        if updates.get("role") == "ansatt":
            raise HTTPException(status_code=400, detail="Du kan ikke fjerne din egen admin-rolle")
        if updates.get("is_active") is False:
            raise HTTPException(status_code=400, detail="Du kan ikke deaktivere din egen konto")
    if not updates:
        raise HTTPException(status_code=400, detail="Ingen felter ├Ñ oppdatere")

    fields = []
    params = []
    for key, value in updates.items():
        fields.append(f"{key} = ?")
        params.append(1 if key == 'is_active' and isinstance(value, bool) else value)
    params.append(user_id)
    await _execute_commit(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", tuple(params))

    if updates.get("is_active") is False:
        await _execute_commit("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
    if "name" in updates:
        await _execute_commit("UPDATE sales SET employee_name = ? WHERE employee_id = ?", (updates["name"], user_id))

    await log_activity(admin.user_id, admin.email, "user_updated", {"user_id": user_id, "changes": list(updates.keys())})
    return {"ok": True}


@api_router.patch("/users/{user_id}/password")
async def update_user_password(user_id: str, payload: UserPasswordUpdate, admin: User = Depends(require_admin)):
    target = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Bruker ikke funnet")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Passord må ha minst 8 tegn")

    await _execute_commit("UPDATE users SET password_hash = ? WHERE user_id = ?", (_hash_password(payload.password), user_id))
    await _execute_commit("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
    await log_activity(admin.user_id, admin.email, "user_password_updated", {"user_id": user_id})
    return {"ok": True}


@api_router.post("/users/{user_id}/revoke-sessions")
async def revoke_user_sessions(user_id: str, admin: User = Depends(require_admin)):
    target = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Bruker ikke funnet")
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Du kan ikke kaste ut deg selv")
    cur = await run_in_threadpool(_execute, "DELETE FROM user_sessions WHERE user_id = ?", (user_id,), True)
    await log_activity(admin.user_id, admin.email, "user_kicked", {"user_id": user_id, "sessions_revoked": cur.rowcount})
    return {"ok": True, "revoked": cur.rowcount}


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(require_admin)):
    target = await _fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Bruker ikke funnet")
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Du kan ikke slette din egen konto")
    await _execute_commit("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
    await _execute_commit("DELETE FROM users WHERE user_id = ?", (user_id,))
    await log_activity(admin.user_id, admin.email, "user_deleted", {"user_id": user_id, "email": target["email"]})
    return {"ok": True}


# =============== Activity Log (admin) ===============
@api_router.get("/activity-log")
async def get_activity_log(user: User = Depends(require_admin), limit: int = 200):
    rows = await _fetch_all("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    return [_row_to_activity(row) for row in rows]


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
    rows = await _fetch_all("SELECT * FROM sales ORDER BY sale_date DESC", ())
    docs = [_row_to_sale(row) for row in rows]
    headers, data_rows = _sales_rows(docs)
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(headers)
    writer.writerows(data_rows)
    await log_activity(user.user_id, user.email, "export_csv", {"count": len(data_rows)})
    output = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(output),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dynasty8_salg.csv"},
    )


@api_router.get("/export/xlsx")
async def export_xlsx(user: User = Depends(require_admin)):
    rows = await _fetch_all("SELECT * FROM sales ORDER BY sale_date DESC", ())
    docs = [_row_to_sale(row) for row in rows]
    headers, data_rows = _sales_rows(docs)
    wb = Workbook()
    ws = wb.active
    ws.title = "Salg"
    ws.append(headers)
    for r in data_rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    await log_activity(user.user_id, user.email, "export_xlsx", {"count": len(data_rows)})
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dynasty8_salg.xlsx"},
    )


# =============== Root ===============
@api_router.get("/")
async def root():
    return {
        "app": "Dynasty 8 AS",
        "status": "ok",
        "database_path": str(DATABASE_PATH),
        "persistent_storage": str(DATABASE_PATH).startswith("/data/"),
    }


app.include_router(api_router)

if FRONTEND_BUILD_DIR.exists():
    static_dir = FRONTEND_BUILD_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        requested_path = (FRONTEND_BUILD_DIR / full_path).resolve()
        build_root = FRONTEND_BUILD_DIR.resolve()
        if requested_path.is_file() and build_root in requested_path.parents:
            return FileResponse(requested_path)

        return FileResponse(FRONTEND_BUILD_DIR / "index.html")

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
    _db_connection.close()
