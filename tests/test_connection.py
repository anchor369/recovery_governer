from backend.db import get_connection


with get_connection() as connection:
    with connection.cursor() as cursor:
        cursor.execute("""
    SELECT
        order_id,
        customer_id,
        amount_minor,
        status
    FROM orders;
""")

        result = cursor.fetchall()
        for row in result:
            print(row)