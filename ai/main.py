import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
import io
import numpy as np

app = FastAPI(title="EvaluaPlus AI Service")

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def es_imagen_valida(file: UploadFile) -> bool:
    if file.content_type and file.content_type.startswith("image/"):
        return True
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in EXTENSIONES_VALIDAS:
            return True
    return False


def clasificar_estado(porcentaje: float) -> str:
    if porcentaje <= 20:
        return "Excelente"
    elif porcentaje <= 50:
        return "Aceptable"
    else:
        return "Deteriorado"


@app.get("/")
def health_check():
    return {"status": "ok", "servicio": "EvaluaPlus AI"}


@app.post("/analizar")
async def analizar_imagen(file: UploadFile = File(...)):
    if not es_imagen_valida(file):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_array = np.array(image)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo procesar la imagen.")

    # TODO: Reemplazar con inferencia real de Anomalib cuando el modelo esté entrenado
    porcentaje_deterioro = 0.0
    zonas_danadas = []

    estado = clasificar_estado(porcentaje_deterioro)

    return {
        "porcentaje_deterioro": porcentaje_deterioro,
        "estado": estado,
        "zonas_danadas": zonas_danadas,
        "nota": "Modelo pendiente de entrenamiento. Resultado simulado."
    }