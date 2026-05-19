import os
import io
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
import numpy as np
import cv2
from pathlib import Path
import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision import models

app = FastAPI(
    title="EvaluaPlus AI Service",
    root_path="/ia"
)

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MODEL_PATH = Path("model/evalua_plus_model.pth")

modelo = None
clases = ["defect", "good"]

# ══════════════════════════════════════════════════════════════════════════════
#   CALIBRACIÓN  (ajustables por variables de entorno)
#
#   CALIB_OFFSET  → resta puntos al score bruto del modelo.
#                   Si madera perfecta da 46 %, pon CALIB_OFFSET=30
#                   para que quede en ~16 % (Excelente).
#                   Rango útil: -50 a +50. Default: 0
#
#   CALIB_SCALE   → multiplica el score DESPUÉS del offset.
#                   < 1.0 comprime el rango (todo baja).
#                   > 1.0 amplía el rango (diferencias más pronunciadas).
#                   Default: 1.0
#
#   UMBRAL_EXCELENTE  → por debajo de este % → "Excelente".  Default: 25
#   UMBRAL_ACEPTABLE  → por debajo de este % → "Aceptable".  Default: 60
#                       por encima               → "Deteriorado"
# ══════════════════════════════════════════════════════════════════════════════

CALIB_OFFSET      = float(os.getenv("CALIB_OFFSET",      "30"))   # restar al score bruto
CALIB_SCALE       = float(os.getenv("CALIB_SCALE",       "1.0"))
UMBRAL_EXCELENTE  = float(os.getenv("UMBRAL_EXCELENTE",  "25"))
UMBRAL_ACEPTABLE  = float(os.getenv("UMBRAL_ACEPTABLE",  "60"))

transform = T.Compose([
    T.Resize((256, 256)),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]),
])


# ══════════════════════════════════════════════════════════════════════════════
#   PIPELINE DE PREPROCESAMIENTO
# ══════════════════════════════════════════════════════════════════════════════

def recortar_fondo(img_bgr: np.ndarray,
                   umbral_blanco: int = 230,
                   margen: int = 12) -> np.ndarray:

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, umbral_blanco, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)

    contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return img_bgr

    contorno_mayor = max(contornos, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(contorno_mayor)
    img_h, img_w = img_bgr.shape[:2]

    if (w * h) < (img_w * img_h * 0.2):
        return img_bgr

    x  = max(0,     x - margen)
    y  = max(0,     y - margen)
    x2 = min(img_w, x + w + margen * 2)
    y2 = min(img_h, y + h + margen * 2)

    return img_bgr[y:y2, x:x2]


def aplicar_filtros(img_bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)

    img_clahe = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    gaussian = cv2.GaussianBlur(img_clahe, (0, 0), sigmaX=2)
    img_sharp = cv2.addWeighted(img_clahe, 1.3, gaussian, -0.3, 0)

    return img_sharp


def preprocesar(pil_image: Image.Image):
    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    h_orig, w_orig = img_bgr.shape[:2]

    img_recortada = recortar_fondo(img_bgr)
    img_filtrada  = aplicar_filtros(img_recortada)

    h_new, w_new = img_filtrada.shape[:2]
    recorte_aplicado = (h_new != h_orig or w_new != w_orig)

    pil_final = Image.fromarray(cv2.cvtColor(img_filtrada, cv2.COLOR_BGR2RGB))
    return pil_final, img_filtrada, recorte_aplicado


def bgr_a_base64(img_bgr: np.ndarray) -> str:
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(img_rgb)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#   CALIBRACIÓN DEL SCORE
# ══════════════════════════════════════════════════════════════════════════════

def calibrar_score(prob_defecto_raw: float) -> float:
    """
    Aplica offset y escala al score bruto del modelo.
    El resultado queda pinzado en [0, 100].
    """
    score = prob_defecto_raw * 100.0
    score = (score - CALIB_OFFSET) * CALIB_SCALE
    return round(max(0.0, min(100.0, score)), 2)


def clasificar_estado(porcentaje: float) -> str:
    if porcentaje <= UMBRAL_EXCELENTE:
        return "Excelente"
    elif porcentaje <= UMBRAL_ACEPTABLE:
        return "Aceptable"
    else:
        return "Deteriorado"


# ══════════════════════════════════════════════════════════════════════════════
#   CARGA DEL MODELO
# ══════════════════════════════════════════════════════════════════════════════

def cargar_modelo():
    global modelo, clases

    if not MODEL_PATH.exists():
        print(f"⚠️ Modelo no encontrado en {MODEL_PATH}")
        return

    try:
        checkpoint = torch.load(str(MODEL_PATH), map_location="cpu", weights_only=False)
        clases = checkpoint.get("clases", ["defect", "good"])
        arquitectura = checkpoint.get("arquitectura", "resnet50")

        if arquitectura == "resnet50":
            model = models.resnet50(weights=None)
            model.fc = nn.Sequential(
                nn.Dropout(0.5),
                nn.Linear(model.fc.in_features, 2)
            )
        elif arquitectura == "resnet34":
            model = models.resnet34(weights=None)
            model.fc = nn.Sequential(
                nn.Dropout(0.5),
                nn.Linear(model.fc.in_features, 2)
            )
        elif arquitectura == "efficientnet_b0":
            model = models.efficientnet_b0(weights=None)
            model.classifier = nn.Sequential(
                nn.Dropout(0.5),
                nn.Linear(model.classifier[1].in_features, 2)
            )
        else:
            model = models.resnet50(weights=None)
            model.fc = nn.Sequential(
                nn.Dropout(0.5),
                nn.Linear(model.fc.in_features, 2)
            )

        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        modelo = model

        print(f"✅ Modelo '{arquitectura}' cargado. Clases: {clases}")
        print(f"   Calibración → offset={CALIB_OFFSET}  scale={CALIB_SCALE}")
        print(f"   Umbrales    → Excelente≤{UMBRAL_EXCELENTE}%  Aceptable≤{UMBRAL_ACEPTABLE}%")

    except Exception as e:
        print(f"⚠️ Error cargando modelo: {e}")
        modelo = None


@app.on_event("startup")
async def startup_event():
    cargar_modelo()


# ══════════════════════════════════════════════════════════════════════════════
#   HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def es_imagen_valida(file: UploadFile) -> bool:
    if file.content_type and file.content_type.startswith("image/"):
        return True
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in EXTENSIONES_VALIDAS:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
#   ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def health_check():
    return {
        "status":          "ok",
        "servicio":        "EvaluaPlus AI",
        "modelo_cargado":  modelo is not None,
        "calibracion": {
            "offset":           CALIB_OFFSET,
            "scale":            CALIB_SCALE,
            "umbral_excelente": UMBRAL_EXCELENTE,
            "umbral_aceptable": UMBRAL_ACEPTABLE,
        },
    }


@app.post("/preprocesar")
async def preprocesar_imagen(file: UploadFile = File(...)):
    if not es_imagen_valida(file):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    try:
        contents  = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo abrir la imagen.")

    try:
        pil_proc, img_bgr, recorte = preprocesar(pil_image)
        w_orig, h_orig = pil_image.size
        w_proc, h_proc = pil_proc.size

        return {
            "imagen_base64":       bgr_a_base64(img_bgr),
            "dimensiones_original":  {"w": w_orig, "h": h_orig},
            "dimensiones_procesada": {"w": w_proc, "h": h_proc},
            "recorte_aplicado":      recorte,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en preprocesamiento: {e}")


@app.post("/analizar")
async def analizar_imagen(file: UploadFile = File(...)):
    if not es_imagen_valida(file):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    try:
        contents  = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo procesar la imagen.")

    try:
        pil_procesada, _, _ = preprocesar(pil_image)
    except Exception as e:
        print(f"⚠️ Preprocesamiento falló: {e}")
        pil_procesada = pil_image

    if modelo is not None:
        try:
            tensor = transform(pil_procesada).unsqueeze(0)

            with torch.no_grad():
                output        = modelo(tensor)
                probabilidades = torch.softmax(output, dim=1)[0]

            idx_defect   = clases.index("defect") if "defect" in clases else 0
            prob_raw     = float(probabilidades[idx_defect])
            porcentaje   = calibrar_score(prob_raw)

            print(
                f"🔍 prob_defecto_raw={prob_raw:.4f} ({prob_raw*100:.1f}%) "
                f"→ calibrado={porcentaje}%  estado={clasificar_estado(porcentaje)}"
            )

            return {
                "porcentaje_deterioro": porcentaje,
                "estado":               clasificar_estado(porcentaje),
                "zonas_danadas":        [],
                "modelo":               "ResNet50",
            }

        except Exception as e:
            print(f"❌ Error en inferencia: {e}")

    return {
        "porcentaje_deterioro": 0.0,
        "estado":               "Excelente",
        "zonas_danadas":        [],
        "nota":                 "Modelo no disponible. Resultado simulado.",
    }


# ══════════════════════════════════════════════════════════════════════════════
#   ENDPOINT DE DIAGNÓSTICO  –  útil para ajustar la calibración
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/diagnostico")
async def diagnostico(file: UploadFile = File(...)):
    """
    Devuelve el score BRUTO del modelo junto con el calibrado.
    Útil para afinar CALIB_OFFSET sin reiniciar el servicio.
    """
    if not es_imagen_valida(file):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    try:
        contents  = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo abrir la imagen.")

    if modelo is None:
        raise HTTPException(status_code=503, detail="Modelo no cargado.")

    try:
        pil_procesada, _, recorte = preprocesar(pil_image)
    except Exception:
        pil_procesada = pil_image
        recorte = False

    tensor = transform(pil_procesada).unsqueeze(0)
    with torch.no_grad():
        output         = modelo(tensor)
        probabilidades = torch.softmax(output, dim=1)[0]

    idx_defect = clases.index("defect") if "defect" in clases else 0
    idx_good   = clases.index("good")   if "good"   in clases else 1

    prob_defecto_raw = float(probabilidades[idx_defect])
    prob_good_raw    = float(probabilidades[idx_good])
    score_calibrado  = calibrar_score(prob_defecto_raw)

    return {
        "score_bruto_defecto_pct":  round(prob_defecto_raw * 100, 2),
        "score_bruto_good_pct":     round(prob_good_raw    * 100, 2),
        "score_calibrado_pct":      score_calibrado,
        "estado_calibrado":         clasificar_estado(score_calibrado),
        "recorte_aplicado":         recorte,
        "calibracion_activa": {
            "offset":           CALIB_OFFSET,
            "scale":            CALIB_SCALE,
            "umbral_excelente": UMBRAL_EXCELENTE,
            "umbral_aceptable": UMBRAL_ACEPTABLE,
        },
    }