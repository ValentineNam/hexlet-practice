-- Выполнять целиком в транзакции; etl.py обеспечивает ее автоматически.
CREATE SCHEMA IF NOT EXISTS practice_2026_10_05;
SET LOCAL search_path TO practice_2026_10_05;
SELECT pg_advisory_xact_lock(20261005, 1);

CREATE OR REPLACE FUNCTION clean_text(value TEXT) RETURNS TEXT
LANGUAGE SQL IMMUTABLE STRICT AS $$
    SELECT btrim(regexp_replace(value, '[[:space:]]+', ' ', 'g'));
$$;

CREATE SEQUENCE IF NOT EXISTS partners_partner_id_seq AS INTEGER;
CREATE TABLE IF NOT EXISTS partners (
    partner_id INTEGER PRIMARY KEY DEFAULT nextval('partners_partner_id_seq'),
    company_name VARCHAR(255) NOT NULL,
    partner_type VARCHAR(30) NOT NULL,
    inn VARCHAR(12) NOT NULL UNIQUE,
    contact_email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20),
    rating INTEGER NOT NULL DEFAULT 0,
    address VARCHAR(500),
    director VARCHAR(255)
);
ALTER SEQUENCE partners_partner_id_seq OWNED BY partners.partner_id;
ALTER TABLE partners ALTER COLUMN partner_id SET DEFAULT nextval('partners_partner_id_seq');

-- Старые дробные/пустые рейтинги не округляем и не заменяем молча.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM partners WHERE rating IS NULL OR rating < 0
               OR rating > 2147483647 OR rating <> trunc(rating)) THEN
        RAISE EXCEPTION 'Рейтинг содержит несовместимые значения; требуется ручное согласование';
    END IF;
END;
$$;
ALTER TABLE partners DROP CONSTRAINT IF EXISTS partners_rating_check;
ALTER TABLE partners DROP CONSTRAINT IF EXISTS partners_inn_check;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'practice_2026_10_05' AND table_name = 'partners'
                 AND column_name = 'rating' AND data_type <> 'integer') THEN
        ALTER TABLE partners ALTER COLUMN rating TYPE INTEGER USING rating::INTEGER;
    END IF;
END;
$$;
ALTER TABLE partners ALTER COLUMN rating SET DEFAULT 0;
ALTER TABLE partners ALTER COLUMN rating SET NOT NULL;
ALTER TABLE partners DROP CONSTRAINT IF EXISTS partners_valid;
ALTER TABLE partners ADD CONSTRAINT partners_valid CHECK (
    partner_id > 0 AND rating >= 0
    AND company_name <> '' AND company_name = clean_text(company_name)
    AND partner_type IN ('ООО', 'АО', 'ЗАО', 'ПАО', 'ИП')
    AND inn ~ '^([0-9]{10}|[0-9]{12})$'
    AND contact_email ~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'
    AND contact_email = lower(contact_email)
    AND (phone IS NULL OR phone = clean_text(phone))
    AND (address IS NULL OR address = clean_text(address))
    AND (director IS NULL OR director = clean_text(director))
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL UNIQUE,
    list_price DECIMAL(12, 2) NOT NULL
);
ALTER TABLE products DROP CONSTRAINT IF EXISTS products_valid;
ALTER TABLE products ADD CONSTRAINT products_valid CHECK (
    product_id > 0 AND product_name <> '' AND product_name = clean_text(product_name)
    AND list_price >= 0 AND list_price < 'Infinity'::NUMERIC
);

CREATE TABLE IF NOT EXISTS sales_history (
    sale_id INTEGER PRIMARY KEY,
    partner_id INTEGER NOT NULL REFERENCES partners(partner_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    sale_date DATE NOT NULL,
    quantity INTEGER NOT NULL,
    sale_amount DECIMAL(22, 2) NOT NULL
);
-- Переход с предыдущей версии: сохраняем известную сумму старой продажи.
-- Для новых CSV сумма берется непосредственно из amount, без вычисления цены.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'practice_2026_10_05' AND table_name = 'sales_history'
                 AND column_name = 'unit_price_at_sale') THEN
        ALTER TABLE sales_history RENAME COLUMN unit_price_at_sale TO sale_amount;
        ALTER TABLE sales_history ALTER COLUMN sale_amount TYPE DECIMAL(22, 2);
        UPDATE sales_history SET sale_amount = sale_amount * quantity;
    END IF;
END;
$$;
ALTER TABLE sales_history DROP CONSTRAINT IF EXISTS sales_valid;
ALTER TABLE sales_history ADD CONSTRAINT sales_valid CHECK (
    sale_id > 0 AND quantity > 0 AND isfinite(sale_date)
    AND sale_amount >= 0 AND sale_amount < 'Infinity'::NUMERIC
);
CREATE INDEX IF NOT EXISTS ix_sales_history_partner_date ON sales_history(partner_id, sale_date DESC);
CREATE INDEX IF NOT EXISTS ix_sales_history_product ON sales_history(product_id);

-- Отдельные демонстрационные справочники. Значения загружает etl.py
-- из существующего material_calculator.py, не из CSV заказчика.
CREATE TABLE IF NOT EXISTS product_types (
    product_type_id INTEGER PRIMARY KEY CHECK (product_type_id > 0),
    coefficient NUMERIC NOT NULL CHECK (coefficient > 0 AND coefficient < 'Infinity'::NUMERIC),
    data_source TEXT NOT NULL CHECK (data_source IN ('demo', 'customer'))
);
CREATE TABLE IF NOT EXISTS material_types (
    material_type_id INTEGER PRIMARY KEY CHECK (material_type_id > 0),
    scrap_percentage NUMERIC NOT NULL CHECK (scrap_percentage >= 0 AND scrap_percentage < 'Infinity'::NUMERIC),
    data_source TEXT NOT NULL CHECK (data_source IN ('demo', 'customer'))
);

-- Общие проверки используются и импортом, и независимым SQL-аудитом.
CREATE OR REPLACE VIEW data_quality_checks AS
SELECT 'broken_foreign_keys' AS check_name, count(*) AS invalid_count
FROM sales_history s LEFT JOIN partners p USING (partner_id) LEFT JOIN products pr USING (product_id)
WHERE p.partner_id IS NULL OR pr.product_id IS NULL
UNION ALL
SELECT 'invalid_partners', count(*) FROM partners
WHERE partner_id <= 0 OR rating IS NULL OR rating < 0
   OR company_name = '' OR company_name <> clean_text(company_name)
   OR partner_type NOT IN ('ООО', 'АО', 'ЗАО', 'ПАО', 'ИП')
   OR inn !~ '^([0-9]{10}|[0-9]{12})$'
   OR contact_email !~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'
   OR contact_email <> lower(contact_email)
   OR phone <> clean_text(phone) OR address <> clean_text(address) OR director <> clean_text(director)
UNION ALL
SELECT 'invalid_products', count(*) FROM products
WHERE product_id <= 0 OR product_name = '' OR product_name <> clean_text(product_name)
   OR list_price < 0 OR NOT list_price < 'Infinity'::NUMERIC
UNION ALL
SELECT 'invalid_sales', count(*) FROM sales_history
WHERE sale_id <= 0 OR quantity <= 0 OR sale_date IS NULL OR NOT isfinite(sale_date)
   OR sale_amount < 0 OR NOT sale_amount < 'Infinity'::NUMERIC
UNION ALL
SELECT 'duplicate_inn', count(*) FROM (SELECT inn FROM partners GROUP BY inn HAVING count(*) > 1) d
UNION ALL
SELECT 'duplicate_email', count(*) FROM (SELECT lower(contact_email) FROM partners GROUP BY lower(contact_email) HAVING count(*) > 1) d
UNION ALL
SELECT 'invalid_product_types', count(*) FROM product_types
WHERE product_type_id <= 0 OR coefficient <= 0 OR NOT coefficient < 'Infinity'::NUMERIC
   OR data_source NOT IN ('demo', 'customer')
UNION ALL
SELECT 'invalid_material_types', count(*) FROM material_types
WHERE material_type_id <= 0 OR scrap_percentage < 0 OR NOT scrap_percentage < 'Infinity'::NUMERIC
   OR data_source NOT IN ('demo', 'customer');
