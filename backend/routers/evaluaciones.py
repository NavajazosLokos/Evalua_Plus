import os
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Evaluation, AIResult, DetectedDamage
from routers.auth import get_usuario_actual

router = APIRouter(prefix="/evaluaciones", tags=["Evaluaciones"])

AI_URL = os.getenv("AI_SERVICE_URL", "http://ai:8001")

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def es_imagen_valida(file: UploadFile) -> bool:
    # Verificar por content_type
    if file.content_type and file.content_type.startswith("image/"):
        return True
    # Verificar por extensión si el content_type no está disponible
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in EXTENSIONES_VALIDAS:
            return True
    return False


@router.post("/analizar")
async def analizar_material(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: User = Depends(get_usuario_actual)
):
    if not es_imagen_valida(file):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (jpg, jpeg, png, webp).")

    contenido = await file.read()

    # 1. Crear registro de evaluación en estado "pending"
    evaluacion = Evaluation(
        user_id=usuario.id,
        image_path=file.filename,
        status="pending"
    )
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)

    # 2. Llamar al servicio de IA
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AI_URL}/analizar",
                files={"file": (file.filename, contenido, file.content_type or "image/jpeg")}
            )
            response.raise_for_status()
            resultado = response.json()
    except httpx.ConnectError:
        evaluacion.status = "error"
        db.commit()
        raise HTTPException(status_code=503, detail="El servicio de IA no está disponible.")
    except httpx.HTTPStatusError as e:
        evaluacion.status = "error"
        db.commit()
        raise HTTPException(status_code=502, detail=f"Error en el servicio de IA: {e}")

    # 3. Guardar resultado de IA
    ai_result = AIResult(
        evaluation_id=evaluacion.id,
        damage_type=resultado.get("estado"),
        confidence=resultado.get("porcentaje_deterioro"),
        description=resultado.get("nota")
    )
    db.add(ai_result)
    db.commit()
    db.refresh(ai_result)

    # 4. Guardar zonas dañadas
    for zona in resultado.get("zonas_danadas", []):
        damage = DetectedDamage(
            ai_result_id=ai_result.id,
            label=zona.get("label"),
            x_min=zona.get("x_min"),
            y_min=zona.get("y_min"),
            x_max=zona.get("x_max"),
            y_max=zona.get("y_max"),
            confidence=zona.get("confidence")
        )
        db.add(damage)

    # 5. Actualizar estado a "completed"
    evaluacion.status = "completed"
    db.commit()

    return {
        "evaluacion_id": evaluacion.id,
        "archivo": file.filename,
        "usuario": usuario.email,
        "resultado": resultado
    }


@router.get("/historial")
def historial_evaluaciones(
    db: Session = Depends(get_db),
    usuario: User = Depends(get_usuario_actual)
):
    evaluaciones = db.query(Evaluation).filter(
        Evaluation.user_id == usuario.id
    ).order_by(Evaluation.created_at.desc()).all()
    return evaluaciones