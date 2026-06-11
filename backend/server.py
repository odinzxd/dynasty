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


def _row_to_deal(row):
    if row is None:
        return None
    data = dict(row)
    data['is_active'] = bool(data.get('is_active', 1))
    return data


def _row_to_announcement(row):
    if row is None:
        return None
    data = dict(row)
    data['is_active'] = bool(data.get('is_active', 1))
    return data


def _row_to_ledger(row):
    if row is None:
        return None
    data = dict(row)
    return data


def _row_to_cash_register(row):
    if row is None:
        return None
    data = dict(row)
    return data


def _row_to_product(row):
    if row is None:
        return None
    data = dict(row)
    data["is_active"] = bool(data.get("is_active", 1))
    return data


def _row_to_coupon(row):
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
            coupon_code TEXT,
            coupon_discount REAL NOT NULL DEFAULT 0,
            surcharge_label TEXT,
            surcharge_amount REAL NOT NULL DEFAULT 0,
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
    if not _column_exists("sales", "coupon_code"):
        _execute("ALTER TABLE sales ADD COLUMN coupon_code TEXT", commit=True)
    if not _column_exists("sales", "coupon_discount"):
        _execute("ALTER TABLE sales ADD COLUMN coupon_discount REAL NOT NULL DEFAULT 0", commit=True)
    if not _column_exists("sales", "surcharge_label"):
        _execute("ALTER TABLE sales ADD COLUMN surcharge_label TEXT", commit=True)
    if not _column_exists("sales", "surcharge_amount"):
        _execute("ALTER TABLE sales ADD COLUMN surcharge_amount REAL NOT NULL DEFAULT 0", commit=True)
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
        CREATE TABLE IF NOT EXISTS discount_coupons (
            coupon_id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            discount_kind TEXT NOT NULL,
            discount_value REAL NOT NULL,
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
    _execute('''
        CREATE TABLE IF NOT EXISTS company_deals (
            deal_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            terms TEXT,
            discount_percent REAL,
            valid_from TEXT,
            valid_to TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''', commit=True)

    _execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            announcement_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''', commit=True)

    # Ledger / accounting table
    _execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            entry_id TEXT PRIMARY KEY,
            entry_date TEXT NOT NULL,
            amount REAL NOT NULL,
            direction TEXT NOT NULL,
            category TEXT,
            description TEXT,
            employee_id TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''', commit=True)

    _execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)', commit=True)
    _execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sales_employee_id ON sales(employee_id)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sales_sale_date ON sales(sale_date)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales(product_id)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_sale_products_category ON sale_products(category)', commit=True)
    _execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_discount_coupons_code ON discount_coupons(code)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_ledger_entry_date ON ledger(entry_date)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_company_deals_active ON company_deals(is_active)', commit=True)
    _execute('CREATE INDEX IF NOT EXISTS idx_announcements_active ON announcements(is_active)', commit=True)
    _ensure_initial_admin()
    _ensure_default_products()


_init_db()

app = FastAPI(title="Dynasty 8 AS - Sales Management")
api_router = APIRouter(prefix="/api")

# =============== Price Matrix ===============
ZONES = ["Jessheim", "Lillestrøm", "Nedre Oslo", "Øvre Oslo", "Oslo Sentrum", "Oslo Sentralt"]
PACKAGES = ["Shell", "IPL", "MLO"]

PRICE_MATRIX = {
    "Jessheim":     {"Shell": 5000,  "IPL": 5500,  "MLO": 8000},
    "Lillestrøm":   {"Shell": 5500,  "IPL": 9000,  "MLO": 13000},
    "Nedre Oslo":   {"Shell": 7000,  "IPL": 11000, "MLO": 15000},
    "Øvre Oslo":    {"Shell": 9000,  "IPL": 15000,  "MLO": 22000},
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
    coupon_code: Optional[str] = None
    coupon_discount: float = 0
    surcharge_label: Optional[str] = None
    surcharge_amount: float = 0
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
    coupon_code: Optional[str] = None
    surcharge_label: Optional[str] = None
    surcharge_amount: float = 0
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
    coupon_code: Optional[str] = None
    surcharge_label: Optional[str] = None
    surcharge_amount: Optional[float] = None
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


class DiscountCoupon(BaseModel):
    model_config = ConfigDict(extra="ignore")
    coupon_id: str
    code: str
    name: str
    discount_kind: Literal["percent", "amount"]
    discount_value: float
    is_active: bool = True
    created_at: str
    updated_at: str


class DiscountCouponCreate(BaseModel):
    code: str
    name: str
    discount_kind: Literal["percent", "amount"]
    discount_value: float
    is_active: bool = True


class DiscountCouponUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    discount_kind: Optional[Literal["percent", "amount"]] = None
    discount_value: Optional[float] = None
    is_active: Optional[bool] = None


class LedgerEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entry_id: str
    entry_date: str
    amount: float
    direction: Literal["in", "out"]
    category: Optional[str] = None
    description: Optional[str] = None
    employee_id: str
    employee_name: str
    created_at: str


class LedgerCreate(BaseModel):
    entry_date: str
    amount: float
    direction: Literal["in", "out"]
    category: Optional[str] = None
    description: Optional[str] = None


class CashRegister(BaseModel):
    register_id: str
    balance: float
    note: Optional[str] = None
    updated_at: str
    updated_by: str
    updated_by_name: str


class CashRegisterUpdate(BaseModel):
    balance: float
    note: Optional[str] = None


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


async def _get_coupon(coupon_code: Optional[str], include_inactive: bool = False):
    if not coupon_code:
        return None
    code = coupon_code.strip().upper()
    if include_inactive:
        return await _fetch_one("SELECT * FROM discount_coupons WHERE upper(code) = ?", (code,))
    return await _fetch_one("SELECT * FROM discount_coupons WHERE upper(code) = ? AND is_active = 1", (code,))


async def calculate_price(
    product_id_or_name: str,
    addons: List[str],
    tenant_count: int,
    discount_type: Optional[str],
    coupon_code: Optional[str] = None,
    surcharge_amount: float = 0,
):
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
    surcharge = max(float(surcharge_amount or 0), 0)
    subtotal += surcharge
    pct = 0.0
    if discount_type == "5":
        pct = 5
    elif discount_type == "10":
        pct = 10
    elif discount_type == "15":
        pct = 15
    elif discount_type == "ansatt":
        pct = 20
    total_after_discount = subtotal * (1 - pct / 100.0)

    coupon = await _get_coupon(coupon_code)
    coupon_discount = 0.0
    if coupon:
        if coupon["discount_kind"] == "percent":
            coupon_discount = total_after_discount * (float(coupon["discount_value"]) / 100.0)
        else:
            coupon_discount = float(coupon["discount_value"])
        coupon_discount = min(coupon_discount, total_after_discount)

    total = max(total_after_discount - coupon_discount, 0)
    return float(base), round(total, 2), pct, _row_to_product(product), _row_to_coupon(coupon), round(coupon_discount, 2), surcharge


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
    coupons = [_row_to_coupon(row) for row in await _fetch_all("SELECT * FROM discount_coupons ORDER BY code", ())]
    active_coupons = [c for c in coupons if c["is_active"]]
    return {
        "zones": ZONES,
        "packages": PACKAGES,
        "matrix": PRICE_MATRIX,
        "product_categories": ["Shell", "IPL", "MLO"],
        "products": products,
        "active_products": active_products,
        "coupons": coupons,
        "active_coupons": active_coupons,
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
    coupon_code = body.get("coupon_code")
    surcharge_amount = float(body.get("surcharge_amount") or 0)
    base, total, pct, product, coupon, coupon_discount, surcharge = await calculate_price(
        product_id, addons, tenant_count, discount_type, coupon_code, surcharge_amount,
    )
    return {
        "base_price": base,
        "total_price": total,
        "discount_percent": pct,
        "product": product,
        "coupon": coupon,
        "coupon_discount": coupon_discount,
        "surcharge_amount": surcharge,
    }


# =============== Sales Endpoints ===============
@api_router.post("/sales", response_model=Sale)
async def create_sale(payload: SaleCreate, user: User = Depends(get_current_user)):
    product_key = payload.product_id or payload.package
    base, total, pct, product, coupon, coupon_discount, surcharge = await calculate_price(
        product_key, payload.addons, payload.tenant_count, payload.discount_type,
        payload.coupon_code, payload.surcharge_amount,
    )
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
        "coupon_code": coupon["code"] if coupon else None,
        "coupon_discount": coupon_discount,
        "surcharge_label": payload.surcharge_label,
        "surcharge_amount": surcharge,
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
        "INSERT INTO sales (sale_id, customer_name, phone, address, zone, product_id, package, addons, tenant_count, discount_type, coupon_code, coupon_discount, surcharge_label, surcharge_amount, discount_percent, base_price, total_price, sale_date, employee_id, employee_name, employee_email, comment, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sale["sale_id"], sale["customer_name"], sale["phone"], sale["address"], sale["zone"], sale["product_id"], sale["package"], _json_dump(sale["addons"]), sale["tenant_count"], sale["discount_type"], sale["coupon_code"], sale["coupon_discount"], sale["surcharge_label"], sale["surcharge_amount"], sale["discount_percent"], sale["base_price"], sale["total_price"], sale["sale_date"], sale["employee_id"], sale["employee_name"], sale["employee_email"], sale["comment"], sale["status"], sale["created_at"], sale["updated_at"],
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
    if any(k in updates for k in ["product_id", "package", "addons", "tenant_count", "discount_type", "coupon_code", "surcharge_amount"]):
        product_key = merged.get("product_id") or merged.get("package")
        base, total, pct, product, coupon, coupon_discount, surcharge = await calculate_price(
            product_key, merged.get("addons", []),
            int(merged.get("tenant_count") or 0), merged.get("discount_type"),
            merged.get("coupon_code"), float(merged.get("surcharge_amount") or 0),
        )
        merged["product_id"] = product["product_id"]
        merged["package"] = f'{product["category"]} - {product["name"]}'
        merged["coupon_code"] = coupon["code"] if coupon else None
        merged["coupon_discount"] = coupon_discount
        merged["surcharge_amount"] = surcharge
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


# =============== Ledger / Accounting ===============

@api_router.get("/ledger")
async def list_ledger(user: User = Depends(get_current_user)):
    docs = await _fetch_all("SELECT * FROM ledger ORDER BY entry_date DESC LIMIT 1000", ())
    entries = [_row_to_ledger(row) for row in docs]
    return entries


@api_router.post("/ledger", response_model=LedgerEntry)
async def create_ledger_entry(payload: LedgerCreate, user: User = Depends(get_current_user)):
    entry = {
        "entry_id": f"led_{uuid.uuid4().hex[:12]}",
        "entry_date": payload.entry_date,
        "amount": float(payload.amount),
        "direction": payload.direction,
        "category": payload.category,
        "description": payload.description,
        "employee_id": user.user_id,
        "employee_name": user.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await _execute_commit(
        "INSERT INTO ledger (entry_id, entry_date, amount, direction, category, description, employee_id, employee_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry["entry_id"], entry["entry_date"], entry["amount"], entry["direction"], entry["category"], entry["description"], entry["employee_id"], entry["employee_name"], entry["created_at"],
        ),
    )
    await log_activity(user.user_id, user.email, "ledger_created", {"entry_id": entry["entry_id"], "amount": entry["amount"], "direction": entry["direction"]})
    return LedgerEntry(**entry)


@api_router.get("/cash-register", response_model=CashRegister)
async def get_cash_register(user: User = Depends(get_current_user)):
    row = await _fetch_one("SELECT * FROM cash_register WHERE register_id = ?", ("main",))
    if row is None:
        now = datetime.now(timezone.utc).isoformat()
        _execute_commit("INSERT INTO cash_register (register_id, balance, note, updated_at, updated_by, updated_by_name) VALUES (?, ?, ?, ?, ?, ?)",
                        ("main", 0.0, "Første oppdatering", now, user.user_id, user.name))
        row = await _fetch_one("SELECT * FROM cash_register WHERE register_id = ?", ("main",))
    return CashRegister(**_row_to_cash_register(row))


@api_router.post("/cash-register", response_model=CashRegister)
async def update_cash_register(payload: CashRegisterUpdate, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    _execute_commit("INSERT OR REPLACE INTO cash_register (register_id, balance, note, updated_at, updated_by, updated_by_name) VALUES (?, ?, ?, ?, ?, ?)",
                    ("main", float(payload.balance), payload.note, now, user.user_id, user.name))
    row = await _fetch_one("SELECT * FROM cash_register WHERE register_id = ?", ("main",))
    await log_activity(user.user_id, user.email, "cash_register_updated", {"balance": payload.balance, "note": payload.note})
    return CashRegister(**_row_to_cash_register(row))


# =============== Stats ===============
@api_router.get("/stats/dashboard")
async def stats_dashboard(user: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    docs = await _fetch_all("SELECT * FROM sales WHERE employee_id = ? AND sale_date = ? ORDER BY created_at DESC", (user.user_id, today))
    sales = [_row_to_sale(row) for row in docs]
    total_revenue = sum(d.get("total_price", 0) for d in sales if d.get("status") not in ("kansellert", "under_behandling"))
    count = len([d for d in sales if d.get("status") not in ("kansellert", "under_behandling")])
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
    active = [d for d in sales if d.get("status") not in ("kansellert", "under_behandling")]
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


@api_router.get("/stats/range")
async def stats_range(start: Optional[str] = None, end: Optional[str] = None, user: User = Depends(require_admin)):
    """Return revenue per day and total revenue for sales between start and end (inclusive).
    Dates should be in YYYY-MM-DD format. If end is omitted it's set to today. If start omitted it's unbounded.
    """
    if end:
        end_date = end
    else:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    params = []
    where = []
    where.append("status NOT IN ('kansellert', 'under_behandling')")
    where.append("sale_date <= ?")
    params.append(end_date)
    if start:
        where.append("sale_date >= ?")
        params.append(start)

    where_clause = " AND ".join(where)
    rows = await _fetch_all(f"SELECT * FROM sales WHERE {where_clause} ORDER BY sale_date", tuple(params))
    docs = [_row_to_sale(row) for row in rows]
    per_day = {}
    total = 0
    for d in docs:
        sd = d.get("sale_date", "")
        if len(sd) >= 10:
            day = sd[:10]
        else:
            day = sd
        per_day.setdefault(day, {"day": day, "revenue": 0, "count": 0})
        per_day[day]["revenue"] += d.get("total_price", 0)
        per_day[day]["count"] += 1
        total += d.get("total_price", 0)

    return {
        "total_revenue": total,
        "total_count": len(docs),
        "per_day": sorted(per_day.values(), key=lambda x: x["day"]),
        "sales": [Sale(**doc).model_dump(mode="json") for doc in docs],
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


# =============== Company Deals ===============
@api_router.get("/company-deals")
async def list_company_deals(user: User = Depends(get_current_user)):
    rows = await _fetch_all("SELECT * FROM company_deals WHERE is_active = 1 ORDER BY created_at DESC", ())
    return [_row_to_deal(row) for row in rows]


@api_router.post("/company-deals")
async def create_company_deal(body: dict, user: User = Depends(require_admin)):
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    if not title or not description:
        raise HTTPException(status_code=400, detail="Tittel og beskrivelse kreves")
    now = datetime.now(timezone.utc).isoformat()
    deal_id = f"deal_{uuid.uuid4().hex[:12]}"
    await _execute_commit(
        "INSERT INTO company_deals (deal_id, title, description, terms, discount_percent, valid_from, valid_to, is_active, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (deal_id, title, description, body.get("terms"), body.get("discount_percent") or None, body.get("valid_from"), body.get("valid_to"), 1, user.user_id, now),
    )
    row = await _fetch_one("SELECT * FROM company_deals WHERE deal_id = ?", (deal_id,))
    await log_activity(user.user_id, user.email, "company_deal_created", {"deal_id": deal_id})
    return _row_to_deal(row)


@api_router.patch("/company-deals/{deal_id}")
async def update_company_deal(deal_id: str, body: dict, user: User = Depends(require_admin)):
    existing = await _fetch_one("SELECT * FROM company_deals WHERE deal_id = ?", (deal_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Avtale ikke funnet")
    updates = {}
    for k in ("title", "description", "terms", "discount_percent", "valid_from", "valid_to", "is_active"):
        if k in body:
            updates[k] = body[k]
    if not updates:
        raise HTTPException(status_code=400, detail="Ingen felter å oppdatere")
    fields = []
    params = []
    for key, value in updates.items():
        fields.append(f"{key} = ?")
        params.append(1 if key == "is_active" and value in (True, 1, "1") else value)
    params.append(deal_id)
    await _execute_commit(f"UPDATE company_deals SET {', '.join(fields)} WHERE deal_id = ?", tuple(params))
    row = await _fetch_one("SELECT * FROM company_deals WHERE deal_id = ?", (deal_id,))
    await log_activity(user.user_id, user.email, "company_deal_updated", {"deal_id": deal_id, "changes": list(updates.keys())})
    return _row_to_deal(row)


@api_router.delete("/company-deals/{deal_id}")
async def delete_company_deal(deal_id: str, user: User = Depends(require_admin)):
    existing = await _fetch_one("SELECT * FROM company_deals WHERE deal_id = ?", (deal_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Avtale ikke funnet")
    await _execute_commit("DELETE FROM company_deals WHERE deal_id = ?", (deal_id,))
    await log_activity(user.user_id, user.email, "company_deal_deleted", {"deal_id": deal_id})
    return {"ok": True}


# =============== Announcements ===============
@api_router.get("/announcements")
async def list_announcements(user: User = Depends(get_current_user)):
    rows = await _fetch_all("SELECT * FROM announcements WHERE is_active = 1 ORDER BY created_at DESC", ())
    return [_row_to_announcement(row) for row in rows]


@api_router.post("/announcements")
async def create_announcement(body: dict, user: User = Depends(require_admin)):
    title = (body.get("title") or "").strip()
    content = (body.get("content") or "").strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="Tittel og innhold kreves")
    now = datetime.now(timezone.utc).isoformat()
    announcement_id = f"ann_{uuid.uuid4().hex[:12]}"
    await _execute_commit(
        "INSERT INTO announcements (announcement_id, title, content, is_active, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (announcement_id, title, content, 1, user.user_id, now),
    )
    row = await _fetch_one("SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,))
    await log_activity(user.user_id, user.email, "announcement_created", {"announcement_id": announcement_id})
    return _row_to_announcement(row)


@api_router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, user: User = Depends(require_admin)):
    existing = await _fetch_one("SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Annonse ikke funnet")
    await _execute_commit("DELETE FROM announcements WHERE announcement_id = ?", (announcement_id,))
    await log_activity(user.user_id, user.email, "announcement_deleted", {"announcement_id": announcement_id})
    return {"ok": True}


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


def _normalize_coupon_code(code: str) -> str:
    return code.strip().upper().replace(" ", "-")


@api_router.get("/coupons", response_model=List[DiscountCoupon])
async def list_coupons(user: User = Depends(require_admin)):
    rows = await _fetch_all("SELECT * FROM discount_coupons ORDER BY code", ())
    return [DiscountCoupon(**_row_to_coupon(row)) for row in rows]


@api_router.post("/coupons", response_model=DiscountCoupon)
async def create_coupon(payload: DiscountCouponCreate, user: User = Depends(require_admin)):
    code = _normalize_coupon_code(payload.code)
    name = payload.name.strip()
    if len(code) < 2:
        raise HTTPException(status_code=400, detail="Kupongkode må ha minst 2 tegn")
    if not name:
        raise HTTPException(status_code=400, detail="Navn mangler")
    if payload.discount_value <= 0:
        raise HTTPException(status_code=400, detail="Rabattverdi må være større enn 0")
    if payload.discount_kind == "percent" and payload.discount_value > 100:
        raise HTTPException(status_code=400, detail="Prosentkupong kan ikke være over 100%")

    existing = await _fetch_one("SELECT coupon_id FROM discount_coupons WHERE upper(code) = ?", (code,))
    if existing:
        raise HTTPException(status_code=400, detail="Kupongkoden er allerede i bruk")

    now = datetime.now(timezone.utc).isoformat()
    coupon_id = f"coupon_{uuid.uuid4().hex[:12]}"
    await _execute_commit(
        "INSERT INTO discount_coupons (coupon_id, code, name, discount_kind, discount_value, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (coupon_id, code, name, payload.discount_kind, float(payload.discount_value), 1 if payload.is_active else 0, now, now),
    )
    await log_activity(user.user_id, user.email, "coupon_created", {"coupon_id": coupon_id, "code": code})
    row = await _fetch_one("SELECT * FROM discount_coupons WHERE coupon_id = ?", (coupon_id,))
    return DiscountCoupon(**_row_to_coupon(row))


@api_router.patch("/coupons/{coupon_id}", response_model=DiscountCoupon)
async def update_coupon(coupon_id: str, payload: DiscountCouponUpdate, user: User = Depends(require_admin)):
    existing = await _fetch_one("SELECT * FROM discount_coupons WHERE coupon_id = ?", (coupon_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Kupong ikke funnet")

    updates = payload.model_dump(exclude_unset=True)
    if "code" in updates:
        updates["code"] = _normalize_coupon_code(updates["code"])
        if len(updates["code"]) < 2:
            raise HTTPException(status_code=400, detail="Kupongkode må ha minst 2 tegn")
        duplicate = await _fetch_one("SELECT coupon_id FROM discount_coupons WHERE upper(code) = ? AND coupon_id != ?", (updates["code"], coupon_id))
        if duplicate:
            raise HTTPException(status_code=400, detail="Kupongkoden er allerede i bruk")
    if "name" in updates:
        updates["name"] = updates["name"].strip()
        if not updates["name"]:
            raise HTTPException(status_code=400, detail="Navn mangler")
    if "discount_value" in updates and updates["discount_value"] <= 0:
        raise HTTPException(status_code=400, detail="Rabattverdi må være større enn 0")
    kind = updates.get("discount_kind", existing["discount_kind"])
    value = updates.get("discount_value", existing["discount_value"])
    if kind == "percent" and float(value) > 100:
        raise HTTPException(status_code=400, detail="Prosentkupong kan ikke være over 100%")
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
    params.append(coupon_id)
    await _execute_commit(f"UPDATE discount_coupons SET {', '.join(fields)} WHERE coupon_id = ?", tuple(params))
    await log_activity(user.user_id, user.email, "coupon_updated", {"coupon_id": coupon_id, "changes": list(updates.keys())})
    row = await _fetch_one("SELECT * FROM discount_coupons WHERE coupon_id = ?", (coupon_id,))
    return DiscountCoupon(**_row_to_coupon(row))


@api_router.delete("/coupons/{coupon_id}")
async def delete_coupon(coupon_id: str, user: User = Depends(require_admin)):
    existing = await _fetch_one("SELECT * FROM discount_coupons WHERE coupon_id = ?", (coupon_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Kupong ikke funnet")

    used = await _fetch_one("SELECT COUNT(*) AS count FROM sales WHERE coupon_code = ?", (existing["code"],))
    if used and used["count"] > 0:
        await _execute_commit("UPDATE discount_coupons SET is_active = 0, updated_at = ? WHERE coupon_id = ?", (datetime.now(timezone.utc).isoformat(), coupon_id))
        await log_activity(user.user_id, user.email, "coupon_deactivated", {"coupon_id": coupon_id, "reason": "used_in_sales"})
        return {"ok": True, "deactivated": True}

    await _execute_commit("DELETE FROM discount_coupons WHERE coupon_id = ?", (coupon_id,))
    await log_activity(user.user_id, user.email, "coupon_deleted", {"coupon_id": coupon_id})
    return {"ok": True, "deleted": True}


# =============== Users (admin) ===============
@api_router.get("/users", response_model=List[User])
async def list_users(user: User = Depends(require_admin)):
    rows = await _fetch_all("SELECT * FROM users ORDER BY created_at DESC", ())
    return [User(**_row_to_user(row)) for row in rows]


@api_router.get("/users/summary")
async def users_summary(user: User = Depends(require_admin)):
    """Return list of users with sales summary (today revenue, this week count), last login and online status."""
    rows = await _fetch_all("SELECT * FROM users ORDER BY name", ())
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    result = []
    for row in rows:
        u = _row_to_user(row)
        uid = row["user_id"]
        # Today's revenue (exclude cancelled / processing)
        td = await _fetch_one(
            "SELECT COALESCE(SUM(total_price), 0) AS revenue FROM sales WHERE employee_id = ? AND sale_date = ? AND status NOT IN ('kansellert', 'under_behandling')",
            (uid, today),
        )
        # This week's sales count
        wk = await _fetch_one(
            "SELECT COUNT(*) AS week_count FROM sales WHERE employee_id = ? AND sale_date >= ? AND sale_date <= ? AND status NOT IN ('kansellert', 'under_behandling')",
            (uid, week_start, today),
        )
        # Last login from activity log
        last = await _fetch_one("SELECT MAX(timestamp) AS last_login FROM activity_log WHERE user_id = ? AND action = 'login'", (uid,))
        # Active sessions
        active = await _fetch_one("SELECT COUNT(*) AS active_sessions FROM user_sessions WHERE user_id = ? AND expires_at > ?", (uid, now.isoformat()))

        u["day_revenue"] = float(td["revenue"] or 0)
        u["week_count"] = int(wk["week_count"] or 0)
        u["last_login"] = last["last_login"] if last and last["last_login"] else None
        u["online"] = bool(active and active["active_sessions"] > 0)
        result.append(u)

    return result


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
        raise HTTPException(status_code=400, detail="Ingen felter å oppdatere")

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
               "Leietakere", "Rabatt %", "Kupong", "Kupongrabatt", "Påslag", "Påslag beløp",
               "Grunnpris", "Totalpris", "Ansatt", "Status", "Kommentar"]
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
            d.get("coupon_code") or "",
            d.get("coupon_discount", 0),
            d.get("surcharge_label") or "",
            d.get("surcharge_amount", 0),
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
