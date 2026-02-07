from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Item
from schemas.item import ItemCreate

router = APIRouter(
    prefix="/items",
    tags=["Items"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    new_item = Item(
        name=item.name,
        description=item.description
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item
