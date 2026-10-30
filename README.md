# Gabriel Fruit Production & Processing — Streamlit Website

A rebuild of the former PHP/MySQL website as a GitHub-friendly Streamlit application with a public product catalog and password-protected Admin Panel.

## What is included

- Responsive public-facing Home, Products, About/Contact, and Admin views
- Product catalog with search and category filtering
- Product fields for name, description, category, price, unit, stock status, featured flag, published/hidden status, and display order
- Multiple photos per product, with primary-image selection and image deletion
- Admin CRUD for products
- Admin-editable website copy, contact details, Vision/Mission, logo, and hero image
- Persistent production storage using Supabase Postgres + Supabase Storage
- Local SQLite/filesystem fallback for development
- Password verification using PBKDF2-HMAC-SHA256; the plain-text admin password is not committed to source
- Basic login attempt throttling within a Streamlit session

## Initial Admin Login

- Username: `admin`
- Password: use the password supplied by the project owner during setup.

The repository stores only a derived PBKDF2 hash for that initial password.

## 1. Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
streamlit run streamlit_app.py
```

Without Supabase credentials, the app automatically uses `data/gabriel_fruit.db` plus `data/uploads/`. This is useful for local testing but should not be treated as permanent storage on Streamlit Community Cloud.

## 2. Create Supabase persistence

1. Create a Supabase project.
2. Open **SQL Editor**.
3. Paste and run `setup_supabase.sql`.
4. In Supabase **Project Settings → API**, copy:
   - Project URL
   - `service_role` key
5. Keep the service-role key private. Do not put it in GitHub.

The SQL file creates:

- `products`
- `product_images`
- `site_settings`
- public `gabriel-media` Storage bucket with a 5 MB image limit and JPG/PNG/WebP allowlist

## 3. Push to GitHub

Create a new GitHub repository and upload/push this entire folder. The `.gitignore` already excludes `secrets.toml`, the local SQLite database, and local uploaded media.

Typical Git commands:

```bash
git init
git add .
git commit -m "Initial Gabriel Fruit Streamlit website"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

## 4. Deploy on Streamlit Community Cloud

1. Go to Streamlit Community Cloud and create an app from your GitHub repository.
2. Set the main file to `streamlit_app.py`.
3. Open **App settings → Secrets** and paste:

```toml
[supabase]
url = "https://YOUR_PROJECT.supabase.co"
key = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
```

4. Save/reboot the app.
5. Open the Admin page and sign in.
6. Add your real products and photos.

## Change the admin password later

Generate a new PBKDF2 hash locally:

```python
from auth import hash_password
print(hash_password("YOUR_NEW_PASSWORD", "YOUR_RANDOM_SALT", 310000))
```

Then add these values to Streamlit Secrets:

```toml
[admin]
username = "admin"
password_hash = "PASTE_THE_GENERATED_HASH"
password_salt = "YOUR_RANDOM_SALT"
password_iterations = 310000
```

Restart the app after changing the secrets.

## Security notes

- Never commit `.streamlit/secrets.toml`.
- Never commit the Supabase `service_role` key.
- The service-role key is used only by Streamlit's server-side Python process.
- The public Storage bucket is intended for product and branding images only.
- Uploaded files are limited to JPG/JPEG, PNG, and WebP and to 5 MB per image in the application and bucket configuration.
- If the site grows into an e-commerce system with customer accounts/payments, replace the simple admin login with a proper identity provider such as Supabase Auth.

## Legacy-content notes

The starter copy reflects the former site: Gabriel Fruit Production and Processing, the Tulunan/Cotabato location, the 2015 establishment statement, the zero-waste positioning, the 2023 FDA licensure statement, and the prior phone/email details. These can all be edited from the Admin Panel.
