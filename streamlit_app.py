from __future__ import annotations

import html
import time
from typing import Any

import streamlit as st

from auth import AuthConfig, verify_credentials
from storage import DEFAULT_SETTINGS, Repository

st.set_page_config(
    page_title="Gabriel Fruit Production and Processing",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def secret(path: str, default: Any = "") -> Any:
    """Safely read nested Streamlit secrets using dot notation."""
    try:
        current: Any = st.secrets
        for part in path.split("."):
            current = current[part]
        return current
    except Exception:
        return default


@st.cache_resource
def get_repo() -> Repository:
    return Repository(
        supabase_url=secret("supabase.url", ""),
        supabase_key=secret("supabase.key", ""),
    )


repo = get_repo()


def money(value: Any) -> str:
    try:
        return f"₱{float(value):,.2f}"
    except Exception:
        return "₱0.00"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --gf-red: #b91c1c;
            --gf-red-dark: #7f1d1d;
            --gf-stone: #1c1917;
            --gf-muted: #78716c;
            --gf-cream: #fafaf9;
        }
        .stApp { background: #fafaf9; }
        #MainMenu, footer { visibility: hidden; }
        [data-testid="stHeader"] { background: rgba(250,250,249,.90); backdrop-filter: blur(10px); }
        .block-container { padding-top: 1.2rem; max-width: 1220px; }
        h1,h2,h3 { letter-spacing: -0.03em; }
        .gf-brandbar {
            display:flex; align-items:center; justify-content:space-between; gap:1rem;
            padding:.35rem 0 .8rem 0; border-bottom:1px solid #e7e5e4;
        }
        .gf-brand { font-size:1.1rem; font-weight:900; letter-spacing:.03em; }
        .gf-brand span { color:var(--gf-red); }
        .gf-chip { display:inline-block; padding:.32rem .7rem; border-radius:999px; background:#fee2e2; color:#991b1b; font-weight:800; font-size:.75rem; }
        .gf-hero {
            min-height: 560px; border-radius: 30px; overflow:hidden; position:relative;
            display:flex; align-items:center; padding:clamp(2rem,6vw,5rem); margin:1.1rem 0 2.5rem;
            background-size:cover; background-position:center; box-shadow:0 30px 70px rgba(28,25,23,.14);
        }
        .gf-hero::before { content:""; position:absolute; inset:0; background:linear-gradient(100deg,rgba(12,10,9,.88),rgba(28,25,23,.58),rgba(127,29,29,.20)); }
        .gf-hero-content { position:relative; z-index:2; max-width:760px; color:white; }
        .gf-hero h1 { font-size:clamp(3.3rem,8vw,7.2rem); line-height:.88; margin:.45rem 0 1rem; font-weight:950; }
        .gf-hero h1 span { color:#ef4444; }
        .gf-hero p { font-size:clamp(1rem,2vw,1.35rem); color:#e7e5e4; max-width:620px; }
        .gf-section-title { font-size:clamp(2.2rem,4vw,4rem); font-weight:950; margin:.2rem 0 .4rem; }
        .gf-rule { width:74px; height:6px; border-radius:10px; background:var(--gf-red); margin:.65rem 0 1.6rem; }
        .gf-card {
            background:white; border:1px solid #e7e5e4; border-radius:24px; padding:1.2rem;
            box-shadow:0 14px 35px rgba(28,25,23,.06); height:100%;
        }
        .gf-price { font-size:1.55rem; font-weight:900; color:var(--gf-red-dark); margin:.3rem 0; }
        .gf-muted { color:var(--gf-muted); }
        .gf-contact { background:#1c1917; color:white; border-radius:30px; padding:clamp(1.5rem,5vw,4rem); margin-top:2rem; }
        .gf-contact a { color:#fecaca !important; }
        .gf-admin-note { padding:1rem 1.1rem; border:1px solid #f59e0b; background:#fffbeb; border-radius:14px; }
        .gf-stat { background:white; border:1px solid #e7e5e4; border-radius:18px; padding:1rem; }
        div[data-testid="stForm"] { border:1px solid #e7e5e4; border-radius:20px; padding:1rem; background:#fff; }
        .stButton > button, .stFormSubmitButton > button { border-radius:999px; font-weight:800; }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background:#b91c1c; border-color:#b91c1c; }
        @media (max-width: 720px) {
            .gf-hero { min-height:470px; border-radius:22px; }
            .gf-contact { border-radius:22px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brandbar(settings: dict[str, str]) -> None:
    logo = settings.get("logo_url", "")
    left = ""
    if logo:
        left += f'<img src="{html.escape(logo, quote=True)}" alt="Logo" style="height:44px;max-width:150px;object-fit:contain;margin-right:12px;vertical-align:middle">'
    brand = html.escape(settings.get("brand_name") or "GABRIEL FRUIT")
    brand = brand.replace("FRUIT", "<span>FRUIT</span>")
    left += f'<span class="gf-brand">{brand}</span>'
    st.markdown(
        f'<div class="gf-brandbar"><div>{left}</div><div class="gf-chip">Tulunan • Cotabato</div></div>',
        unsafe_allow_html=True,
    )


def primary_image(product: dict[str, Any]) -> str | None:
    images = product.get("images") or []
    if not images:
        return None
    preferred = next((x for x in images if x.get("is_primary")), None)
    return str((preferred or images[0]).get("image_url") or "") or None


def render_home(settings: dict[str, str], products: list[dict[str, Any]]) -> None:
    hero = html.escape(settings.get("hero_image_url") or DEFAULT_SETTINGS["hero_image_url"], quote=True)
    brand = html.escape(settings.get("brand_name") or "GABRIEL FRUIT")
    if "FRUIT" in brand:
        brand = brand.replace("FRUIT", "<span>FRUIT</span>")
    tagline = html.escape(settings.get("tagline") or "Production & Processing")
    kicker = html.escape(settings.get("hero_kicker") or "Pure. Local. Sustainable.")
    st.markdown(
        f"""
        <section class="gf-hero" style="background-image:url('{hero}')">
          <div class="gf-hero-content">
            <div class="gf-chip">{kicker}</div>
            <h1>{brand}</h1>
            <p>{tagline}</p>
            <p style="margin-top:1.4rem;font-size:1rem">Discover our locally produced and processed fruit products.</p>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    featured = [p for p in products if p.get("featured")][:3]
    if featured:
        st.markdown('<div class="gf-section-title">Featured Products</div><div class="gf-rule"></div>', unsafe_allow_html=True)
        render_product_grid(featured)

    st.markdown('<div class="gf-section-title" style="margin-top:3rem">Our Story</div><div class="gf-rule"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.markdown(f"### {settings.get('about_title') or 'Pure. Local. Sustainable.'}")
        st.write(settings.get("about_body", ""))
        if settings.get("about_highlight"):
            st.info(settings["about_highlight"])
    with c2:
        st.markdown(
            """
            <div class="gf-card">
              <div style="font-size:2rem">🌱</div>
              <h3>Locally Rooted</h3>
              <p class="gf-muted">A family-owned enterprise based in Tulunan, Cotabato.</p>
              <hr style="border:none;border-top:1px solid #e7e5e4;margin:1rem 0">
              <div style="font-size:2rem">♻️</div>
              <h3>Zero-Waste Philosophy</h3>
              <p class="gf-muted">Sustainability remains part of the company story and product direction.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_product_grid(products: list[dict[str, Any]]) -> None:
    if not products:
        st.info("No products are published yet. An administrator can add products from the Admin panel.")
        return
    for start in range(0, len(products), 3):
        row = products[start : start + 3]
        cols = st.columns(3)
        for col, product in zip(cols, row):
            with col:
                with st.container(border=True):
                    image = primary_image(product)
                    if image:
                        st.image(image, use_container_width=True)
                    else:
                        st.markdown(
                            "<div style='height:190px;border-radius:14px;background:#f5f5f4;display:flex;align-items:center;justify-content:center;font-size:3rem'>🍊</div>",
                            unsafe_allow_html=True,
                        )
                    if product.get("featured"):
                        st.caption("⭐ Featured")
                    st.subheader(product.get("name", "Unnamed product"))
                    st.caption(f"{product.get('category', 'General')} • {product.get('stock_status', 'Available')}")
                    st.markdown(f"<div class='gf-price'>{money(product.get('price'))} <span style='font-size:.9rem;color:#78716c'>/ {html.escape(str(product.get('unit') or 'item'))}</span></div>", unsafe_allow_html=True)
                    if product.get("description"):
                        st.write(product["description"])
                    images = product.get("images") or []
                    if len(images) > 1:
                        with st.expander(f"View gallery ({len(images)} photos)"):
                            for img in images:
                                st.image(img["image_url"], caption=img.get("alt_text") or product.get("name"), use_container_width=True)


def render_products(products: list[dict[str, Any]]) -> None:
    st.markdown('<div class="gf-section-title">Our Products</div><div class="gf-rule"></div>', unsafe_allow_html=True)
    if not products:
        render_product_grid([])
        return
    categories = sorted({str(p.get("category") or "General") for p in products})
    c1, c2 = st.columns([2, 1])
    with c1:
        query = st.text_input("Search products", placeholder="Search by product name or description...")
    with c2:
        chosen = st.selectbox("Category", ["All"] + categories)
    filtered = products
    if chosen != "All":
        filtered = [p for p in filtered if (p.get("category") or "General") == chosen]
    if query.strip():
        q = query.strip().lower()
        filtered = [p for p in filtered if q in str(p.get("name", "")).lower() or q in str(p.get("description", "")).lower()]
    st.caption(f"{len(filtered)} product(s) shown")
    render_product_grid(filtered)


def render_about_contact(settings: dict[str, str]) -> None:
    st.markdown('<div class="gf-section-title">About Gabriel Fruit</div><div class="gf-rule"></div>', unsafe_allow_html=True)
    st.markdown(f"### {settings.get('about_title', '')}")
    st.write(settings.get("about_body", ""))
    if settings.get("about_highlight"):
        st.success(settings["about_highlight"])

    if settings.get("vision") or settings.get("mission"):
        v1, v2 = st.columns(2)
        with v1:
            if settings.get("vision"):
                st.markdown("### Vision")
                st.write(settings["vision"])
        with v2:
            if settings.get("mission"):
                st.markdown("### Mission")
                st.write(settings["mission"])

    st.markdown(
        f"""
        <div class="gf-contact">
          <h2 style="font-size:2.5rem;margin-top:0">Contact Us</h2>
          <p>{html.escape(settings.get('order_note',''))}</p>
          <p>📍 <b>Visit:</b> {html.escape(settings.get('location',''))}</p>
          <p>📞 <b>Call:</b> {html.escape(settings.get('phone',''))}</p>
          <p>✉️ <b>Email:</b> {html.escape(settings.get('email',''))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def auth_config() -> AuthConfig:
    return AuthConfig(
        username=str(secret("admin.username", "admin")),
        password_hash=str(secret("admin.password_hash", AuthConfig().password_hash)),
        salt=str(secret("admin.password_salt", AuthConfig().salt)),
        iterations=int(secret("admin.password_iterations", AuthConfig().iterations)),
    )


def admin_login() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True
    st.markdown("## Administrator Login")
    st.caption("Use the administrator credentials configured for this deployment.")

    locked_until = float(st.session_state.get("admin_locked_until", 0.0))
    now = time.time()
    if locked_until > now:
        st.error("Too many failed attempts. Please try again shortly.")
        return False

    with st.form("admin_login_form"):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submitted:
        if verify_credentials(username, password, auth_config()):
            st.session_state["admin_authenticated"] = True
            st.session_state["admin_failures"] = 0
            st.rerun()
        else:
            failures = int(st.session_state.get("admin_failures", 0)) + 1
            st.session_state["admin_failures"] = failures
            if failures >= 5:
                st.session_state["admin_locked_until"] = time.time() + 60
                st.session_state["admin_failures"] = 0
            st.error("Invalid username or password.")
    return False


def product_payload_from_form(prefix: str, existing: dict[str, Any] | None = None) -> dict[str, Any] | None:
    existing = existing or {}
    name = st.text_input("Product name *", value=str(existing.get("name", "")), key=f"{prefix}_name")
    description = st.text_area("Description", value=str(existing.get("description", "")), height=130, key=f"{prefix}_description")
    c1, c2, c3 = st.columns(3)
    with c1:
        category = st.text_input("Category", value=str(existing.get("category", "General")), key=f"{prefix}_category")
    with c2:
        price = st.number_input("Price (PHP)", min_value=0.0, value=float(existing.get("price", 0) or 0), step=1.0, key=f"{prefix}_price")
    with c3:
        unit = st.text_input("Unit", value=str(existing.get("unit", "item")), key=f"{prefix}_unit", help="Examples: bottle, pack, jar, kg")
    c4, c5, c6 = st.columns(3)
    with c4:
        status_options = ["Available", "Low Stock", "Pre-order", "Out of Stock", "Seasonal"]
        current = str(existing.get("stock_status", "Available"))
        status_index = status_options.index(current) if current in status_options else 0
        stock_status = st.selectbox("Stock status", status_options, index=status_index, key=f"{prefix}_stock")
    with c5:
        featured = st.checkbox("Featured", value=bool(existing.get("featured", False)), key=f"{prefix}_featured")
    with c6:
        active = st.checkbox("Published", value=bool(existing.get("active", True)), key=f"{prefix}_active")
    sort_order = st.number_input("Display order", min_value=0, value=int(existing.get("sort_order", 0) or 0), step=1, key=f"{prefix}_sort")
    if not name.strip():
        return None
    return {
        "name": name,
        "description": description,
        "category": category,
        "price": price,
        "unit": unit,
        "stock_status": stock_status,
        "featured": featured,
        "active": active,
        "sort_order": sort_order,
    }


def render_admin_products() -> None:
    products = repo.list_products(include_inactive=True)
    st.markdown("### Product Management")
    st.caption("Create, edit, publish/unpublish, feature, reorder, and remove products and their images.")

    with st.expander("➕ Add a new product", expanded=not products):
        with st.form("create_product_form", clear_on_submit=True):
            payload = product_payload_from_form("new")
            images = st.file_uploader(
                "Product pictures (up to 5 MB each)",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key="new_images",
            )
            submitted = st.form_submit_button("Create product", type="primary")
        if submitted:
            if payload is None:
                st.error("Product name is required.")
            else:
                try:
                    product_id = repo.create_product(payload)
                    if images:
                        repo.add_product_images(product_id, images, alt_text=payload["name"])
                    st.success("Product created.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not create product: {exc}")

    if not products:
        st.info("No products yet.")
        return

    labels = {str(p["id"]): f"{p['name']} — {money(p.get('price'))}{'' if p.get('active') else ' [Hidden]'}" for p in products}
    selected_id = st.selectbox("Select a product to edit", list(labels), format_func=lambda x: labels[x])
    selected = repo.get_product(selected_id)
    if not selected:
        st.warning("Product not found.")
        return

    st.markdown("#### Edit details")
    with st.form(f"edit_product_{selected_id}"):
        payload = product_payload_from_form(f"edit_{selected_id}", selected)
        new_images = st.file_uploader(
            "Add more pictures",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"edit_images_{selected_id}",
        )
        saved = st.form_submit_button("Save changes", type="primary")
    if saved:
        if payload is None:
            st.error("Product name is required.")
        else:
            try:
                repo.update_product(selected_id, payload)
                if new_images:
                    repo.add_product_images(selected_id, new_images, alt_text=payload["name"])
                st.success("Product updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not update product: {exc}")

    selected = repo.get_product(selected_id) or selected
    images = selected.get("images") or []
    st.markdown("#### Product pictures")
    if not images:
        st.caption("No pictures uploaded.")
    else:
        for image in images:
            c1, c2, c3 = st.columns([2.5, 1, 1])
            with c1:
                st.image(image["image_url"], width=220)
                if image.get("is_primary"):
                    st.caption("Primary image")
            with c2:
                if not image.get("is_primary") and st.button("Make primary", key=f"primary_{image['id']}"):
                    repo.set_primary_image(selected_id, str(image["id"]))
                    st.rerun()
            with c3:
                if st.button("Delete image", key=f"delete_img_{image['id']}"):
                    repo.delete_image(str(image["id"]))
                    st.rerun()

    st.divider()
    st.markdown("#### Danger zone")
    confirm = st.checkbox(f"I understand this will permanently delete “{selected['name']}” and its uploaded pictures.", key=f"confirm_delete_{selected_id}")
    if st.button("Delete product permanently", disabled=not confirm, key=f"delete_product_{selected_id}"):
        repo.delete_product(selected_id)
        st.success("Product deleted.")
        st.rerun()


def render_admin_settings() -> None:
    settings = {**DEFAULT_SETTINGS, **repo.get_settings()}
    st.markdown("### Website Content & Branding")
    with st.form("settings_form"):
        company_name = st.text_input("Company name", value=settings["company_name"])
        brand_name = st.text_input("Hero brand name", value=settings["brand_name"])
        tagline = st.text_input("Tagline", value=settings["tagline"])
        hero_kicker = st.text_input("Hero badge text", value=settings["hero_kicker"])
        about_title = st.text_input("About title", value=settings["about_title"])
        about_body = st.text_area("About description", value=settings["about_body"], height=120)
        about_highlight = st.text_area("About highlight", value=settings["about_highlight"], height=90)
        vision = st.text_area("Vision (optional)", value=settings.get("vision", ""), height=90)
        mission = st.text_area("Mission (optional)", value=settings.get("mission", ""), height=90)
        location = st.text_input("Location", value=settings["location"])
        phone = st.text_input("Phone", value=settings["phone"])
        email = st.text_input("Email", value=settings["email"])
        facebook_url = st.text_input("Facebook URL (optional)", value=settings.get("facebook_url", ""))
        order_note = st.text_area("Order / inquiry note", value=settings["order_note"], height=80)
        hero_url = st.text_input("Hero image URL", value=settings["hero_image_url"])
        logo_url = st.text_input("Logo URL", value=settings.get("logo_url", ""))
        save = st.form_submit_button("Save website settings", type="primary")
    if save:
        repo.update_settings({
            "company_name": company_name, "brand_name": brand_name, "tagline": tagline,
            "hero_kicker": hero_kicker, "about_title": about_title, "about_body": about_body,
            "about_highlight": about_highlight, "vision": vision, "mission": mission,
            "location": location, "phone": phone, "email": email, "facebook_url": facebook_url,
            "order_note": order_note, "hero_image_url": hero_url, "logo_url": logo_url,
        })
        st.success("Website settings saved.")
        st.rerun()

    st.markdown("#### Upload branding images")
    c1, c2 = st.columns(2)
    with c1:
        logo_file = st.file_uploader("Upload logo", type=["jpg", "jpeg", "png", "webp"], key="site_logo")
        if logo_file and st.button("Use uploaded logo", key="save_logo"):
            try:
                url = repo.upload_site_asset(logo_file, "logo")
                repo.update_settings({"logo_url": url})
                st.success("Logo updated.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c2:
        hero_file = st.file_uploader("Upload hero image", type=["jpg", "jpeg", "png", "webp"], key="site_hero")
        if hero_file and st.button("Use uploaded hero", key="save_hero"):
            try:
                url = repo.upload_site_asset(hero_file, "hero")
                repo.update_settings({"hero_image_url": url})
                st.success("Hero image updated.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def render_admin() -> None:
    if not admin_login():
        return

    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown("# Admin Panel")
        st.caption(f"Storage: {repo.mode.name}")
    with c2:
        if st.button("Sign out", use_container_width=True):
            st.session_state.pop("admin_authenticated", None)
            st.rerun()

    if not repo.mode.persistent:
        st.warning(
            "This deployment is using the local SQLite fallback. It is excellent for testing, but edits can disappear when a hosted Streamlit instance restarts. Configure Supabase before using this in production."
        )

    products = repo.list_products(include_inactive=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Products", len(products))
    m2.metric("Published", sum(1 for p in products if p.get("active")))
    m3.metric("Featured", sum(1 for p in products if p.get("featured")))
    m4.metric("Images", sum(len(p.get("images") or []) for p in products))

    tab1, tab2, tab3 = st.tabs(["Products", "Website Settings", "Deployment"])
    with tab1:
        render_admin_products()
    with tab2:
        render_admin_settings()
    with tab3:
        st.markdown("### Deployment status")
        st.write(f"**Persistence mode:** {repo.mode.name}")
        if repo.mode.persistent:
            st.success("Supabase is configured. Database and uploaded media are persistent.")
        else:
            st.info("Add the Supabase secrets described in README.md to enable persistent database and image storage.")
        st.code(
            "[supabase]\nurl = \"https://YOUR_PROJECT.supabase.co\"\nkey = \"YOUR_SERVICE_ROLE_KEY\"",
            language="toml",
        )
        st.caption("Keep secrets in Streamlit Cloud settings. Never commit them to GitHub.")


def main() -> None:
    inject_css()
    settings = {**DEFAULT_SETTINGS, **repo.get_settings()}
    render_brandbar(settings)

    page = st.radio(
        "Navigation",
        ["Home", "Products", "About & Contact", "Admin"],
        horizontal=True,
        label_visibility="collapsed",
    )

    public_products = repo.list_products(include_inactive=False)
    if page == "Home":
        render_home(settings, public_products)
    elif page == "Products":
        render_products(public_products)
    elif page == "About & Contact":
        render_about_contact(settings)
    else:
        render_admin()


if __name__ == "__main__":
    main()
