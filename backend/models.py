
"""
Modelos de la base de datos para el sistema EvaluaPlus.
Aquí se definen las tablas y sus columnas usando SQLAlchemy.
"""
from sqlalchemy import Column, Integer, String
from database import Base

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
