from fastapi import APIRouter

from backend.api.demo_scenarios import create_demo_scenario
from backend.api.schemas.demo import DemoScenarioRequest, DemoScenarioResponse


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/scenarios", response_model=DemoScenarioResponse)
def create_scenario(request: DemoScenarioRequest):
    return create_demo_scenario(request.preset, request.customer_profile)
