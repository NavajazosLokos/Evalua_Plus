from pydantic import BaseModel

class ItemCreate(BaseModel):
    name: str
    description: str
