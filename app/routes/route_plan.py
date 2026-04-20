from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    RouteGenerateRequest,
    RouteGenerateResponse,
    RouteReplanRequest,
    RouteReplanResponse,
)
from app.services.planner import generate_basic_route, generate_replanned_route

router = APIRouter(prefix="/api/route", tags=["route"])


@router.post("/generate", response_model=RouteGenerateResponse)
def generate_route(data: RouteGenerateRequest, db: Session = Depends(get_db)):
    """
    生成基础导览路线。
    """
    return generate_basic_route(
        db=db,
        available_minutes=data.available_minutes,
        interest=data.interest,
        first_visit=data.first_visit,
        visit_goal=data.visit_goal,
    )


@router.post("/replan", response_model=RouteReplanResponse)
def replan_route(data: RouteReplanRequest, db: Session = Depends(get_db)):
    """
    基于当前所在展区、已访问展区和剩余时间进行中途重规划。
    """
    return generate_replanned_route(
        db=db,
        current_hall_id=data.current_hall_id,
        visited_hall_ids=data.visited_hall_ids,
        remaining_minutes=data.remaining_minutes,
        updated_goal=data.updated_goal,
    )
