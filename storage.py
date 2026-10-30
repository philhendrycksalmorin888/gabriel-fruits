"""Persistence layer for Gabriel Fruit.

Production mode uses Supabase Postgres + Storage. If Supabase is not configured,
a local SQLite + filesystem fallback keeps development friction low. The local
fallback is intentionally labeled non-persistent when hosted on Streamlit.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - allows local syntax/testing without dependency
    Client = Any  # type: ignore
    create_client = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "gabriel_fruit.db"
MEDIA_BUCKET = "gabriel-media"

DEFAULT_SETTINGS: dict[str, str] = {
    "company_name": "Gabriel Fruit Production and Processing",
    "brand_name": "GABRIEL FRUIT",
    "tagline": "Production & Processing",
    "hero_kicker": "Pure. Local. Sustainable.",
    "hero_image_url": "https://images.unsplash.com/photo-1610832958506-aa56338406cd?auto=format&fit=crop&q=80&w=1600",
    "logo_url": "",
    "about_title": "Pure. Local. Sustainable.",
    "about_body": "Established in 2015, we are a family-owned enterprise in Tulunan, Cotabato, dedicated to a zero-waste philosophy.",
    "about_highlight": "Our 2023 FDA licensure stands as a testament to our commitment to international safety standards.",
    "vision": "",
    "mission": "",
    "location": "Tulunan, Cotabato",
    "phone": "+63 918 764 7438",
    "email": "mango.republic9403@gmail.com",
    "facebook_url": "",
    "order_note": "For orders and inquiries, contact us through the details below.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def safe_extension(filename: str, mime_type: str | None = None) -> str:
    ext = Path(filename or "").suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    if ext in allowed:
        return ext
    guessed = mimetypes.guess_extension(mime_type or "") or ".jpg"
    return guessed if guessed in allowed else ".jpg"


@dataclass
class StorageMode:
    name: str
    persistent: bool


class Repository:
    """Unified data/media API used by the Streamlit UI."""

    def __init__(self, supabase_url: str | None = None, supabase_key: str | None = None):
        self.supabase_url = (supabase_url or "").strip()
        self.supabase_key = (supabase_key or "").strip()
        self.sb: Client | None = None
        if self.supabase_url and self.supabase_key and create_client is not None:
            self.sb = create_client(self.supabase_url, self.supabase_key)
            self.mode = StorageMode("Supabase", True)
        else:
            self.mode = StorageMode("Local SQLite", False)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            self._init_local_db()
        self.ensure_default_settings()

    # ---------- Local database helpers ----------
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_local_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'General',
                    price REAL NOT NULL DEFAULT 0,
                    unit TEXT NOT NULL DEFAULT 'item',
                    stock_status TEXT NOT NULL DEFAULT 'Available',
                    featured INTEGER NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS product_images (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    image_url TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    alt_text TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS site_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    # ---------- Settings ----------
    def ensure_default_settings(self) -> None:
        current = self.get_settings()
        missing = {k: v for k, v in DEFAULT_SETTINGS.items() if k not in current}
        if missing:
            self.update_settings(missing)

    def get_settings(self) -> dict[str, str]:
        if self.sb:
            rows = self.sb.table("site_settings").select("setting_key,setting_value").execute().data or []
            return {r["setting_key"]: str(r.get("setting_value") or "") for r in rows}
        with self._conn() as conn:
            rows = conn.execute("SELECT setting_key, setting_value FROM site_settings").fetchall()
        return {r["setting_key"]: r["setting_value"] for r in rows}

    def update_settings(self, values: dict[str, str]) -> None:
        now = utc_now()
        if self.sb:
            payload = [
                {"setting_key": key, "setting_value": str(value), "updated_at": now}
                for key, value in values.items()
            ]
            self.sb.table("site_settings").upsert(payload, on_conflict="setting_key").execute()
            return
        with self._conn() as conn:
            conn.executemany(
                """INSERT INTO site_settings(setting_key, setting_value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(setting_key) DO UPDATE SET
                     setting_value=excluded.setting_value,
                     updated_at=excluded.updated_at""",
                [(k, str(v), now) for k, v in values.items()],
            )

    # ---------- Products ----------
    def list_products(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        if self.sb:
            query = self.sb.table("products").select("*")
            if not include_inactive:
                query = query.eq("active", True)
            rows = query.order("sort_order").order("created_at", desc=True).execute().data or []
        else:
            sql = "SELECT * FROM products"
            params: list[Any] = []
            if not include_inactive:
                sql += " WHERE active = 1"
            sql += " ORDER BY sort_order ASC, created_at DESC"
            with self._conn() as conn:
                rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
            for row in rows:
                row["featured"] = bool(row["featured"])
                row["active"] = bool(row["active"])

        product_ids = [str(r["id"]) for r in rows]
        images = self._images_for_products(product_ids)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for image in images:
            grouped.setdefault(str(image["product_id"]), []).append(image)
        for row in rows:
            row["images"] = grouped.get(str(row["id"]), [])
        return rows

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        if self.sb:
            rows = self.sb.table("products").select("*").eq("id", product_id).limit(1).execute().data or []
            row = rows[0] if rows else None
        else:
            with self._conn() as conn:
                found = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            row = dict(found) if found else None
            if row:
                row["featured"] = bool(row["featured"])
                row["active"] = bool(row["active"])
        if row:
            row["images"] = self._images_for_products([product_id])
        return row

    def create_product(self, payload: dict[str, Any]) -> str:
        product_id = str(uuid.uuid4())
        now = utc_now()
        row = {
            "id": product_id,
            "name": payload["name"].strip(),
            "description": payload.get("description", "").strip(),
            "category": payload.get("category", "General").strip() or "General",
            "price": float(payload.get("price", 0) or 0),
            "unit": payload.get("unit", "item").strip() or "item",
            "stock_status": payload.get("stock_status", "Available").strip() or "Available",
            "featured": bool(payload.get("featured", False)),
            "active": bool(payload.get("active", True)),
            "sort_order": int(payload.get("sort_order", 0) or 0),
            "created_at": now,
            "updated_at": now,
        }
        if self.sb:
            self.sb.table("products").insert(row).execute()
        else:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO products
                    (id,name,description,category,price,unit,stock_status,featured,active,sort_order,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row["id"], row["name"], row["description"], row["category"], row["price"], row["unit"],
                        row["stock_status"], int(row["featured"]), int(row["active"]), row["sort_order"],
                        row["created_at"], row["updated_at"],
                    ),
                )
        return product_id

    def update_product(self, product_id: str, payload: dict[str, Any]) -> None:
        row = {
            "name": payload["name"].strip(),
            "description": payload.get("description", "").strip(),
            "category": payload.get("category", "General").strip() or "General",
            "price": float(payload.get("price", 0) or 0),
            "unit": payload.get("unit", "item").strip() or "item",
            "stock_status": payload.get("stock_status", "Available").strip() or "Available",
            "featured": bool(payload.get("featured", False)),
            "active": bool(payload.get("active", True)),
            "sort_order": int(payload.get("sort_order", 0) or 0),
            "updated_at": utc_now(),
        }
        if self.sb:
            self.sb.table("products").update(row).eq("id", product_id).execute()
        else:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE products SET name=?,description=?,category=?,price=?,unit=?,stock_status=?,
                       featured=?,active=?,sort_order=?,updated_at=? WHERE id=?""",
                    (
                        row["name"], row["description"], row["category"], row["price"], row["unit"],
                        row["stock_status"], int(row["featured"]), int(row["active"]), row["sort_order"],
                        row["updated_at"], product_id,
                    ),
                )

    def delete_product(self, product_id: str) -> None:
        images = self._images_for_products([product_id])
        for image in images:
            self._delete_media_path(image.get("storage_path", ""))
        if self.sb:
            self.sb.table("products").delete().eq("id", product_id).execute()
        else:
            with self._conn() as conn:
                conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    # ---------- Images ----------
    def _images_for_products(self, product_ids: Iterable[str]) -> list[dict[str, Any]]:
        ids = list(product_ids)
        if not ids:
            return []
        if self.sb:
            rows = (
                self.sb.table("product_images")
                .select("*")
                .in_("product_id", ids)
                .order("sort_order")
                .order("created_at")
                .execute()
                .data
                or []
            )
            return rows
        placeholders = ",".join("?" for _ in ids)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM product_images WHERE product_id IN ({placeholders}) ORDER BY sort_order, created_at",
                ids,
            ).fetchall()
        result = [dict(r) for r in rows]
        for row in result:
            row["is_primary"] = bool(row["is_primary"])
        return result

    def add_product_images(self, product_id: str, files: Iterable[Any], alt_text: str = "") -> int:
        existing = self._images_for_products([product_id])
        next_order = max([int(i.get("sort_order", 0)) for i in existing], default=-1) + 1
        count = 0
        for idx, uploaded in enumerate(files):
            raw = uploaded.getvalue()
            if not raw:
                continue
            if len(raw) > 5 * 1024 * 1024:
                raise ValueError(f"{uploaded.name}: image exceeds 5 MB limit")
            mime = getattr(uploaded, "type", None) or "image/jpeg"
            if mime not in {"image/jpeg", "image/png", "image/webp"}:
                raise ValueError(f"{uploaded.name}: unsupported image format")
            ext = safe_extension(uploaded.name, mime)
            path = f"products/{product_id}/{uuid.uuid4().hex}{ext}"
            url = self._upload_media_bytes(path, raw, mime)
            row = {
                "id": str(uuid.uuid4()),
                "product_id": product_id,
                "image_url": url,
                "storage_path": path,
                "alt_text": alt_text.strip(),
                "sort_order": next_order + idx,
                "is_primary": len(existing) == 0 and idx == 0,
                "created_at": utc_now(),
            }
            if self.sb:
                self.sb.table("product_images").insert(row).execute()
            else:
                with self._conn() as conn:
                    conn.execute(
                        """INSERT INTO product_images
                        (id,product_id,image_url,storage_path,alt_text,sort_order,is_primary,created_at)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            row["id"], row["product_id"], row["image_url"], row["storage_path"],
                            row["alt_text"], row["sort_order"], int(row["is_primary"]), row["created_at"],
                        ),
                    )
            count += 1
        return count

    def set_primary_image(self, product_id: str, image_id: str) -> None:
        if self.sb:
            self.sb.table("product_images").update({"is_primary": False}).eq("product_id", product_id).execute()
            self.sb.table("product_images").update({"is_primary": True}).eq("id", image_id).eq("product_id", product_id).execute()
        else:
            with self._conn() as conn:
                conn.execute("UPDATE product_images SET is_primary = 0 WHERE product_id = ?", (product_id,))
                conn.execute("UPDATE product_images SET is_primary = 1 WHERE id = ? AND product_id = ?", (image_id, product_id))

    def delete_image(self, image_id: str) -> None:
        if self.sb:
            rows = self.sb.table("product_images").select("*").eq("id", image_id).limit(1).execute().data or []
            if not rows:
                return
            row = rows[0]
            product_id = str(row["product_id"])
            was_primary = bool(row.get("is_primary"))
            self._delete_media_path(row.get("storage_path", ""))
            self.sb.table("product_images").delete().eq("id", image_id).execute()
        else:
            with self._conn() as conn:
                found = conn.execute("SELECT * FROM product_images WHERE id = ?", (image_id,)).fetchone()
            if not found:
                return
            row = dict(found)
            product_id = str(row["product_id"])
            was_primary = bool(row.get("is_primary"))
            self._delete_media_path(row.get("storage_path", ""))
            with self._conn() as conn:
                conn.execute("DELETE FROM product_images WHERE id = ?", (image_id,))
        if was_primary:
            remaining = self._images_for_products([product_id])
            if remaining:
                self.set_primary_image(product_id, str(remaining[0]["id"]))

    def upload_site_asset(self, uploaded: Any, label: str) -> str:
        raw = uploaded.getvalue()
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError("Image exceeds 5 MB limit")
        mime = getattr(uploaded, "type", None) or "image/jpeg"
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError("Unsupported image format")
        ext = safe_extension(uploaded.name, mime)
        path = f"site/{slugify(label)}-{uuid.uuid4().hex}{ext}"
        return self._upload_media_bytes(path, raw, mime)

    def _upload_media_bytes(self, path: str, raw: bytes, mime: str) -> str:
        if self.sb:
            self.sb.storage.from_(MEDIA_BUCKET).upload(
                path=path,
                file=raw,
                file_options={"content-type": mime, "upsert": "false"},
            )
            public = self.sb.storage.from_(MEDIA_BUCKET).get_public_url(path)
            if isinstance(public, str):
                return public
            return str(getattr(public, "public_url", public))
        target = UPLOAD_DIR / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return str(target)

    def _delete_media_path(self, path: str) -> None:
        if not path:
            return
        try:
            if self.sb:
                self.sb.storage.from_(MEDIA_BUCKET).remove([path])
            else:
                target = UPLOAD_DIR / path
                if target.exists():
                    target.unlink()
        except Exception:
            # Database deletion should not be blocked by an already-missing media object.
            pass
