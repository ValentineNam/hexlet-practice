import os

import psycopg2
from psycopg2.extras import RealDictCursor

from discount_service import calculate_partner_discount


def get_db_connection():
    """Create a PostgreSQL connection using environment variables."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
    )


def get_partner_with_discount(partner_id: int):
    """Select partner totals and compute current discount in a single service layer."""
    query = """
        SELECT
            p.partner_id,
            p.company_name,
            p.contact_email,
            COALESCE(SUM(si.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN shipments AS s
            ON s.partner_id = p.partner_id
        LEFT JOIN shipment_items AS si
            ON si.shipment_id = s.shipment_id
        WHERE p.partner_id = %s
        GROUP BY p.partner_id, p.company_name, p.contact_email
    """

    with get_db_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (partner_id,))
            row = cursor.fetchone()

    if row is None:
        return None

    total_quantity = int(row["total_quantity"])
    discount_percent = calculate_partner_discount(total_quantity)

    return {
        "partner_id": row["partner_id"],
        "company_name": row["company_name"],
        "contact_email": row["contact_email"],
        "total_quantity": total_quantity,
        "discount_percent": discount_percent,
    }


if __name__ == "__main__":
    partner = get_partner_with_discount(2)
    if partner is None:
        print("Partner not found")
    else:
        print(partner)
