-- Gabriel Fruit - Supabase schema
-- Run this once in Supabase > SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.products (
    id uuid primary key,
    name text not null,
    description text not null default '',
    category text not null default 'General',
    price numeric(12,2) not null default 0 check (price >= 0),
    unit text not null default 'item',
    stock_status text not null default 'Available',
    featured boolean not null default false,
    active boolean not null default true,
    sort_order integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.product_images (
    id uuid primary key,
    product_id uuid not null references public.products(id) on delete cascade,
    image_url text not null,
    storage_path text not null,
    alt_text text not null default '',
    sort_order integer not null default 0,
    is_primary boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_products_active_sort on public.products(active, sort_order, created_at desc);
create index if not exists idx_product_images_product on public.product_images(product_id, sort_order, created_at);

create table if not exists public.site_settings (
    setting_key text primary key,
    setting_value text not null default '',
    updated_at timestamptz not null default now()
);

-- The Streamlit backend should connect with the service_role key stored only in
-- Streamlit Secrets. RLS is enabled to block anonymous browser/API writes.
alter table public.products enable row level security;
alter table public.product_images enable row level security;
alter table public.site_settings enable row level security;

-- Public read policies are optional because this Streamlit app reads server-side
-- with the service role. They make the catalog readable if you later add a direct
-- client integration.
drop policy if exists "public read active products" on public.products;
create policy "public read active products"
on public.products for select
to anon
using (active = true);

drop policy if exists "public read product images" on public.product_images;
create policy "public read product images"
on public.product_images for select
to anon
using (exists (select 1 from public.products p where p.id = product_id and p.active = true));

drop policy if exists "public read settings" on public.site_settings;
create policy "public read settings"
on public.site_settings for select
to anon
using (true);

-- Create a public storage bucket for product/site media.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'gabriel-media',
    'gabriel-media',
    true,
    5242880,
    array['image/jpeg','image/png','image/webp']
)
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
