-- =====================================================
-- Final 3NF schema for PostgreSQL
-- =====================================================

DROP TABLE IF EXISTS shipment_items;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS partners;

CREATE TABLE partners (
    partner_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name    VARCHAR(255) NOT NULL,
    inn             VARCHAR(12) NOT NULL UNIQUE CHECK (inn ~ '^[0-9]{10,12}$'),
    contact_email   VARCHAR(255) NOT NULL UNIQUE,
    phone           VARCHAR(20) NOT NULL,
    rating          DECIMAL(3,2) NOT NULL CHECK (rating >= 0 AND rating <= 5)
);

CREATE TABLE products (
    product_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name    VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE shipments (
    shipment_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partner_id      INTEGER NOT NULL,
    shipment_date   DATE NOT NULL,
    total_amount    DECIMAL(12,2) NOT NULL CHECK (total_amount >= 0),

    CONSTRAINT fk_shipments_partners
        FOREIGN KEY (partner_id)
        REFERENCES partners(partner_id)
        ON DELETE RESTRICT
);

CREATE TABLE shipment_items (
    shipment_item_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shipment_id      INTEGER NOT NULL,
    product_id       INTEGER NOT NULL,
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price       DECIMAL(12,4) NOT NULL CHECK (unit_price >= 0),
    line_total       DECIMAL(12,2) NOT NULL CHECK (line_total >= 0),

    CONSTRAINT fk_items_shipments
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_items_products
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_shipment_product UNIQUE (shipment_id, product_id)
);
