from backend.services.payment_truth import evaluate_order_truth


orders_to_test = [
    "O1",
    "O2",
    "O_DOES_NOT_EXIST"
]


for order_id in orders_to_test:
    truth = evaluate_order_truth(order_id)

    print(
        order_id,
        "→",
        truth
    )