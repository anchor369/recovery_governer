from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
)


# ------------------------------------------------
# O200: One confirmed failed payment
# Expected truth: UNPAID
# Expected recovery eligibility: FALSE
# Reason: allow natural retry
# ------------------------------------------------

create_customer(
    customer_id="C200",
    contact_consent=True
)

create_order(
    order_id="O200",
    customer_id="C200",
    amount_minor=100000,
    status="ATTEMPTED"
)

create_payment(
    payment_id="P200",
    order_id="O200",
    method="UPI",
    status="FAILED",
    failure_reason="wrong_pin"
)


# ------------------------------------------------
# O201: Payment still authorized
# Expected truth: UNCERTAIN
# Expected recovery eligibility: FALSE
# ------------------------------------------------

create_customer(
    customer_id="C201",
    contact_consent=True
)

create_order(
    order_id="O201",
    customer_id="C201",
    amount_minor=200000,
    status="ATTEMPTED"
)

create_payment(
    payment_id="P201",
    order_id="O201",
    method="CARD",
    status="AUTHORIZED",
    failure_reason=None
)


# ------------------------------------------------
# O202: Captured payment
# Expected truth: PAID
# Expected recovery eligibility: FALSE
# ------------------------------------------------

create_customer(
    customer_id="C202",
    contact_consent=True
)

create_order(
    order_id="O202",
    customer_id="C202",
    amount_minor=300000,
    status="PAID"
)

create_payment(
    payment_id="P202",
    order_id="O202",
    method="CARD",
    status="CAPTURED",
    failure_reason=None
)


# ------------------------------------------------
# O203: Two confirmed failures
# Expected truth: UNPAID
# Expected recovery eligibility: TRUE
# ------------------------------------------------

create_customer(
    customer_id="C203",
    contact_consent=True
)

create_order(
    order_id="O203",
    customer_id="C203",
    amount_minor=400000,
    status="ATTEMPTED"
)

create_payment(
    payment_id="P203A",
    order_id="O203",
    method="UPI",
    status="FAILED",
    failure_reason="wrong_pin"
)

create_payment(
    payment_id="P203B",
    order_id="O203",
    method="UPI",
    status="FAILED",
    failure_reason="technical_error"
)


print("Truth test data created.")