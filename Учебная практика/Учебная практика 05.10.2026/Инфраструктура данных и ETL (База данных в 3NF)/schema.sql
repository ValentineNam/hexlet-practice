CREATE SCHEMA IF NOT EXISTS practice_2026_10_05;
SET search_path TO practice_2026_10_05;

CREATE TABLE IF NOT EXISTS partners (
    partner_id INTEGER PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    partner_type VARCHAR(30) NOT NULL,
    inn VARCHAR(12) NOT NULL UNIQUE CHECK (inn ~ '^[0-9]{10,12}$'),
    contact_email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20),
    rating DECIMAL(3, 2) NOT NULL DEFAULT 0 CHECK (rating >= 0 AND rating <= 5),
    address VARCHAR(500),
    director VARCHAR(255)
);

ALTER TABLE partners
    ALTER COLUMN rating SET DEFAULT 0;

UPDATE partners
SET rating = 0
WHERE rating IS NULL;

ALTER TABLE partners
    ALTER COLUMN rating SET NOT NULL;

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL UNIQUE,
    list_price DECIMAL(12, 2) NOT NULL CHECK (list_price >= 0)
);

CREATE TABLE IF NOT EXISTS sales_history (
    sale_id INTEGER PRIMARY KEY,
    partner_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    sale_date DATE NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_at_sale DECIMAL(12, 2) NOT NULL CHECK (unit_price_at_sale >= 0),
    CONSTRAINT fk_sales_partner
        FOREIGN KEY (partner_id)
        REFERENCES partners (partner_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_id)
        REFERENCES products (product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_sales_history_partner_date
    ON sales_history (partner_id, sale_date DESC);

CREATE INDEX IF NOT EXISTS ix_sales_history_product
    ON sales_history (product_id);
