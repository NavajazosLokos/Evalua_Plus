import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
import io
import numpy as np
from pathlib import Path
import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision import models

app = FastAPI(title="EvaluaPlus AI Service")

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MODEL_PATH = Path("model/evalua_plus_model.pth")

modelo = None
clases = ["defect", "good"]

transform = T.Compose([
    T.Resize((256, 256)),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def cargar_modelo():
    global modelo, clases
    if MODEL_PATH.exists():
        try:
            checkpoint = torch.load(str(MODEL_PATH), map_location="cpu", weights_only=False)
            clases = checkpoint.get("clases", ["defect", "good"])

            model = models.resnet50(weights=None)
            model.fc = nn.Linear(model.fc.in_features, 2)
            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()
            modelo = model
            print(f"✅ Modelo ResNet50 cargado. Clases: {clases}")
        except Exception as e:
            print(f"⚠️  Error cargando modelo: {e}")
            modelo = None
    else:
        print(f"⚠️  Modelo no encontrado en {MODEL_PATH}")

@app.on_event("startup")
async def startup_event():
    cargar_modelo()

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
    return {
        "status": "ok",
        "servicio": "EvaluaPlus AI",
        "modelo_cargado": modelo is not None
    }

@app.post("/analizar")
async def analizar_imagen(file: UploadFile = File(...)):
    if not es_imagen_valida(file):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo procesar la imagen.")

    if modelo is not None:
        try:
            tensor = transform(image).unsqueeze(0)
            with torch.no_grad():
                output = modelo(tensor)
                probabilidades = torch.softmax(output, dim=1)[0]

            # clases en orden alfabético: defect=0, good=1
            idx_defect = clases.index("defect") if "defect" in clases else 0
            prob_defecto = float(probabilidades[idx_defect])
            porcentaje_deterioro = round(prob_defecto * 100, 2)

            print(f"🔍 prob_defecto: {prob_defecto:.4f} → {porcentaje_deterioro}%")

            estado = clasificar_estado(porcentaje_deterioro)
            return {
                "porcentaje_deterioro": porcentaje_deterioro,
                "estado": estado,
                "zonas_danadas": [],
                "modelo": "ResNet50"
            }
        except Exception as e:
            print(f"❌ Error en inferencia: {e}")

    return {
        "porcentaje_deterioro": 0.0,
        "estado": "Excelente",
        "zonas_danadas": [],
        "nota": "Modelo no disponible. Resultado simulado."
    }