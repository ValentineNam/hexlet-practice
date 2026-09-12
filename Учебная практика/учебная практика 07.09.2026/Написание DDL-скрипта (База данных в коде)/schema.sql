-- =====================================================
-- 3NF: корректная схема для партнеров, товаров,
-- шапки отгрузки и строк отгрузки
-- =====================================================

DROP TABLE IF EXISTS shipment_items;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS partners;

CREATE TABLE partners (
    partner_id      INTEGER PRIMARY KEY,
    company_name    VARCHAR(255) NOT NULL,
    inn             CHAR(10) NOT NULL UNIQUE,
    contact_email   VARCHAR(255) NOT NULL UNIQUE,
    phone           VARCHAR(20) NOT NULL,
    rating          DECIMAL(3,2) NOT NULL CHECK (rating >= 0 AND rating <= 5)
);

CREATE TABLE products (
    product_id      INTEGER PRIMARY KEY,
    product_name    VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE shipments (
    shipment_id     INTEGER PRIMARY KEY,
    partner_id      INTEGER NOT NULL,
    shipment_date   DATE NOT NULL,
    total_amount    DECIMAL(12,2) NOT NULL CHECK (total_amount >= 0),

    CONSTRAINT fk_shipments_partners
        FOREIGN KEY (partner_id)
        REFERENCES partners(partner_id)
        ON DELETE RESTRICT
);

CREATE TABLE shipment_items (
    shipment_item_id INTEGER PRIMARY KEY,
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

-- =====================================================
-- Данные партнеров
-- =====================================================
INSERT INTO partners (partner_id, company_name, inn, contact_email, phone, rating)
VALUES
    (1, 'ООО "Логистик-Экспресс"', '7701234567', 'info@logex.ru', '+79991112233', 4.8),
    (2, 'ИП Петров А.В.', '5001098765', 'petrov_delivery@mail.ru', '+79041112233', 4.2),
    (3, 'ТК "Быстрый Путь"', '7812345678', 'speedway@yandex.ru', '+78125554433', 4.9);

-- =====================================================
-- Данные товаров
-- =====================================================
INSERT INTO products (product_id, product_name)
VALUES
    (1, 'Стиральный порошок "Альфа"'),
    (2, 'Мыло жидкое "Стандарт"'),
    (3, 'Кондиционер для белья');

-- =====================================================
-- Шапки отгрузок
-- =====================================================
INSERT INTO shipments (shipment_id, partner_id, shipment_date, total_amount)
VALUES
    (101, 1, '2026-03-01', 25000.00),
    (102, 2, '2026-03-15', 18000.50),
    (103, 1, '2026-03-20', 10500.00),
    (104, 3, '2026-03-25', 13500.00);

-- =====================================================
-- Позиции отгрузок (строки товаров)
-- =====================================================
INSERT INTO shipment_items (shipment_item_id, shipment_id, product_id, quantity, unit_price, line_total)
VALUES
    (1, 101, 1, 50, 500.0000, 25000.00),
    (2, 102, 2, 200, 90.0025, 18000.50),
    (3, 103, 3, 30, 350.0000, 10500.00),
    (4, 104, 2, 150, 90.0000, 13500.00);