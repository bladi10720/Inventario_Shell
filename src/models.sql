-- Core tables for inventory movements.
-- Run once on a new Neon database.

CREATE TABLE IF NOT EXISTS products (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'Sin categoría',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);

CREATE TABLE IF NOT EXISTS movements (
  id BIGSERIAL PRIMARY KEY,
  type TEXT NOT NULL CHECK (type IN ('IN', 'OUT', 'ADJUST')),
  movement_date DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  product_code TEXT NOT NULL REFERENCES products(code),
  qty INTEGER NOT NULL CHECK (qty > 0),
  actor_role TEXT NOT NULL,
  note TEXT
);

CREATE INDEX IF NOT EXISTS idx_movements_date_type ON movements (movement_date, type);
CREATE INDEX IF NOT EXISTS idx_movements_product_created ON movements (product_code, created_at);

CREATE TABLE IF NOT EXISTS daily_out_closures (
  date DATE PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_role TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'voided')) DEFAULT 'active',
  voided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_daily_out_closures_status ON daily_out_closures (status);

-- Roles and PINs (optional; env PINs still work if no rows match).
CREATE TABLE IF NOT EXISTS roles (
  id SERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roles_active ON roles (active);

CREATE TABLE IF NOT EXISTS role_pins (
  id SERIAL PRIMARY KEY,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  pin TEXT NOT NULL,
  label TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_role_pins_pin UNIQUE (pin)
);

CREATE INDEX IF NOT EXISTS idx_role_pins_pin_active ON role_pins (pin) WHERE active = TRUE;

