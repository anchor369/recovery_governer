from backend.services.recovery_eligibility import (
    evaluate_recovery_eligibility
)


orders_to_test = [
    "O200",
    "O201",
    "O202",
    "O203"
]


for order_id in orders_to_test:
    result = evaluate_recovery_eligibility(order_id)

    print(
        order_id,
        "→",
        result
    )