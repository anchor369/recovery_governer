from fastapi import APIRouter, HTTPException, status

from backend.api.schemas.payments import PaymentEventRequest, PaymentEventResponse
from backend.data_access.payments import (
    ConflictingPaymentEventError,
    record_payment_event,
)


router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/payment-events", response_model=PaymentEventResponse)
def ingest_payment_event(request: PaymentEventRequest):
    try:
        return record_payment_event(**request.model_dump())
    except ConflictingPaymentEventError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "Payment does not exist" in str(error)
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(status_code=status_code, detail=str(error)) from error
