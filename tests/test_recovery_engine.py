from backend.services.recovery_engine import (
    open_recovery_case_if_eligible
)


result = open_recovery_case_if_eligible("O203")

print(result)