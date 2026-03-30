from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
import io
import numpy as np

app = FastAPI(title="EvaluaPlus AI Service")


def clasificar_estado(porcentaje: float) -> str:
    """Clasifica el estado del material según el porcentaje de deterioro."""
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
    """
    Recibe una imagen y devuelve el análisis de deterioro del material.

    Retorna:
    - porcentaje_deterioro: float entre 0 y 100
    - estado: Excelente / Aceptable / Deteriorado
    - zonas_danadas: lista de zonas detectadas (cuando el modelo esté integrado)
    """

    # Validar que sea una imagen
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_array = np.array(image)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo procesar la imagen.")

    # -------------------------------------------------------
    # TODO: Aquí va la inferencia real con Anomalib
    # Una vez que tengan el modelo entrenado, reemplazar este
    # bloque con la inferencia real. Ejemplo:
    #
    # from anomalib.deploy import TorchInferencer
    # inferencer = TorchInferencer(path="model/model.pt")
    # predictions = inferencer.predict(image=img_array)
    # porcentaje = float(predictions.pred_score * 100)
    # zonas = predictions.anomaly_map.tolist()
    # -------------------------------------------------------

    # Respuesta placeholder mientras se integra el modelo
    porcentaje_deterioro = 0.0
    zonas_danadas = []

    estado = clasificar_estado(porcentaje_deterioro)

    return {
        "porcentaje_deterioro": porcentaje_deterioro,
        "estado": estado,
        "zonas_danadas": zonas_danadas,
        "nota": "Modelo pendiente de entrenamiento. Resultado simulado."
    }