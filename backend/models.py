"""
Modelos de la base de datos para el sistema EvaluaPlus.
Alineados con el schema definido en db/init.sql
"""
from sqlalchemy import Column, Integer, String, Float, Numeric, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    created_at = Column(TIMESTAMP, server_default=func.now())

    evaluations = relationship("Evaluation", back_populates="user")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="evaluations")
    ai_results = relationship("AIResult", back_populates="evaluation")
    reports = relationship("Report", back_populates="evaluation")


class AIResult(Base):
    __tablename__ = "ai_results"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    damage_type = Column(String(100))
    confidence = Column(Numeric(5, 2))
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    evaluation = relationship("Evaluation", back_populates="ai_results")
    detected_damages = relationship("DetectedDamage", back_populates="ai_result")


class DetectedDamage(Base):
    __tablename__ = "detected_damages"

    id = Column(Integer, primary_key=True, index=True)
    ai_result_id = Column(Integer, ForeignKey("ai_results.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(100))
    x_min = Column(Float)
    y_min = Column(Float)
    x_max = Column(Float)
    y_max = Column(Float)
    confidence = Column(Numeric(5, 2))

    ai_result = relationship("AIResult", back_populates="detected_damages")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    report_url = Column(String(255))
    generated_at = Column(TIMESTAMP, server_default=func.now())

    evaluation = relationship("Evaluation", back_populates="reports")


# Nota: La tabla sessions existe en la DB pero no se usa
# porque la autenticación se maneja con JWT stateless.
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)