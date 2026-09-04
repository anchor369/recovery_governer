from backend.data_access.payments import (
    create_customer,
    create_order,
)


create_customer("C101")

create_order(
    order_id="O100",
    customer_id="C101",
    amount_minor=150000
)

print("Journey created")