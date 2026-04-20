from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/api/halls", tags=["halls"])


@router.get("/", response_model=List[schemas.MuseumHallBase])
def read_halls(db: Session = Depends(get_db)):
    return crud.get_all_halls(db)