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

app = FastAPI(title="EvaluaPlus AI Service")

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MODEL_PATH = Path("model/evalua_plus_model.pth")

modelo = None
clases = ["defect", "good"]

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

    _, mask = cv2.threshold(
        gray,
        umbral_blanco,
        255,
        cv2.THRESH_BINARY_INV
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (5, 5)
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
    )

    contornos, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contornos:
        return img_bgr

    contorno_mayor = max(contornos, key=cv2.contourArea)

    x, y, w, h = cv2.boundingRect(contorno_mayor)

    img_h, img_w = img_bgr.shape[:2]

    if (w * h) < (img_w * img_h * 0.2):
        return img_bgr

    x = max(0, x - margen)
    y = max(0, y - margen)

    x2 = min(img_w, x + w + margen * 2)
    y2 = min(img_h, y + h + margen * 2)

    return img_bgr[y:y2, x:x2]


def aplicar_filtros(img_bgr: np.ndarray) -> np.ndarray:

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)

    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    l = clahe.apply(l)

    img_clahe = cv2.cvtColor(
        cv2.merge([l, a, b]),
        cv2.COLOR_LAB2BGR
    )

    gaussian = cv2.GaussianBlur(
        img_clahe,
        (0, 0),
        sigmaX=2
    )

    img_sharp = cv2.addWeighted(
        img_clahe,
        1.3,
        gaussian,
        -0.3,
        0
    )

    return img_sharp


def preprocesar(pil_image: Image.Image):

    img_rgb = np.array(
        pil_image.convert("RGB")
    )

    img_bgr = cv2.cvtColor(
        img_rgb,
        cv2.COLOR_RGB2BGR
    )

    h_orig, w_orig = img_bgr.shape[:2]

    img_recortada = recortar_fondo(img_bgr)

    img_filtrada = aplicar_filtros(img_recortada)

    h_new, w_new = img_filtrada.shape[:2]

    recorte_aplicado = (
        h_new != h_orig or
        w_new != w_orig
    )

    pil_final = Image.fromarray(
        cv2.cvtColor(
            img_filtrada,
            cv2.COLOR_BGR2RGB
        )
    )

    return pil_final, img_filtrada, recorte_aplicado


def bgr_a_base64(img_bgr: np.ndarray) -> str:

    img_rgb = cv2.cvtColor(
        img_bgr,
        cv2.COLOR_BGR2RGB
    )

    pil = Image.fromarray(img_rgb)

    buf = io.BytesIO()

    pil.save(
        buf,
        format="JPEG",
        quality=85
    )

    return base64.b64encode(
        buf.getvalue()
    ).decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#   CARGA DEL MODELO
# ══════════════════════════════════════════════════════════════════════════════

def cargar_modelo():

    global modelo, clases

    if MODEL_PATH.exists():

        try:
            checkpoint = torch.load(
                str(MODEL_PATH),
                map_location="cpu",
                weights_only=False
            )

            clases = checkpoint.get(
                "clases",
                ["defect", "good"]
            )

            arquitectura = checkpoint.get(
                "arquitectura",
                "resnet50"
            )

            # ─────────────────────────────────────────────
            # RESNET50
            # ─────────────────────────────────────────────
            if arquitectura == "resnet50":

                model = models.resnet50(
                    weights=None
                )

                model.fc = nn.Sequential(
                    nn.Dropout(0.5),
                    nn.Linear(
                        model.fc.in_features,
                        2
                    )
                )

            # ─────────────────────────────────────────────
            # RESNET34
            # ─────────────────────────────────────────────
            elif arquitectura == "resnet34":

                model = models.resnet34(
                    weights=None
                )

                model.fc = nn.Sequential(
                    nn.Dropout(0.5),
                    nn.Linear(
                        model.fc.in_features,
                        2
                    )
                )

            # ─────────────────────────────────────────────
            # EFFICIENTNET
            # ─────────────────────────────────────────────
            elif arquitectura == "efficientnet_b0":

                model = models.efficientnet_b0(
                    weights=None
                )

                model.classifier = nn.Sequential(
                    nn.Dropout(0.5),
                    nn.Linear(
                        model.classifier[1].in_features,
                        2
                    )
                )

            # ─────────────────────────────────────────────
            # DEFAULT
            # ─────────────────────────────────────────────
            else:

                model = models.resnet50(
                    weights=None
                )

                model.fc = nn.Sequential(
                    nn.Dropout(0.5),
                    nn.Linear(
                        model.fc.in_features,
                        2
                    )
                )

            model.load_state_dict(
                checkpoint["model_state_dict"]
            )

            model.eval()

            modelo = model

            print(
                f"✅ Modelo '{arquitectura}' cargado. "
                f"Clases: {clases}"
            )

        except Exception as e:

            print(
                f"⚠️ Error cargando modelo: {e}"
            )

            modelo = None

    else:

        print(
            f"⚠️ Modelo no encontrado en {MODEL_PATH}"
        )


@app.on_event("startup")
async def startup_event():
    cargar_modelo()


# ══════════════════════════════════════════════════════════════════════════════
#   HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def es_imagen_valida(file: UploadFile) -> bool:

    if (
        file.content_type and
        file.content_type.startswith("image/")
    ):
        return True

    if file.filename:

        ext = os.path.splitext(
            file.filename
        )[1].lower()

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


# ══════════════════════════════════════════════════════════════════════════════
#   ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def health_check():

    return {
        "status": "ok",
        "servicio": "EvaluaPlus AI",
        "modelo_cargado": modelo is not None
    }


@app.post("/preprocesar")
async def preprocesar_imagen(
    file: UploadFile = File(...)
):

    if not es_imagen_valida(file):

        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen."
        )

    try:

        contents = await file.read()

        pil_image = Image.open(
            io.BytesIO(contents)
        ).convert("RGB")

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="No se pudo abrir la imagen."
        )

    try:

        pil_proc, img_bgr, recorte = preprocesar(
            pil_image
        )

        w_orig, h_orig = pil_image.size
        w_proc, h_proc = pil_proc.size

        return {
            "imagen_base64": bgr_a_base64(img_bgr),

            "dimensiones_original": {
                "w": w_orig,
                "h": h_orig
            },

            "dimensiones_procesada": {
                "w": w_proc,
                "h": h_proc
            },

            "recorte_aplicado": recorte,
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error en preprocesamiento: {e}"
        )


@app.post("/analizar")
async def analizar_imagen(
    file: UploadFile = File(...)
):

    if not es_imagen_valida(file):

        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen."
        )

    try:

        contents = await file.read()

        pil_image = Image.open(
            io.BytesIO(contents)
        ).convert("RGB")

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="No se pudo procesar la imagen."
        )

    try:

        pil_procesada, _, _ = preprocesar(
            pil_image
        )

    except Exception as e:

        print(
            f"⚠️ Preprocesamiento falló: {e}"
        )

        pil_procesada = pil_image

    if modelo is not None:

        try:

            tensor = transform(
                pil_procesada
            ).unsqueeze(0)

            with torch.no_grad():

                output = modelo(tensor)

                probabilidades = torch.softmax(
                    output,
                    dim=1
                )[0]

            idx_defect = (
                clases.index("defect")
                if "defect" in clases
                else 0
            )

            prob_defecto = float(
                probabilidades[idx_defect]
            )

            porcentaje_deterioro = round(
                prob_defecto * 100,
                2
            )

            print(
                f"🔍 prob_defecto: "
                f"{prob_defecto:.4f} "
                f"→ {porcentaje_deterioro}%"
            )

            return {
                "porcentaje_deterioro":
                    porcentaje_deterioro,

                "estado":
                    clasificar_estado(
                        porcentaje_deterioro
                    ),

                "zonas_danadas": [],

                "modelo":
                    "ResNet50"
            }

        except Exception as e:

            print(
                f"❌ Error en inferencia: {e}"
            )

    return {
        "porcentaje_deterioro": 0.0,
        "estado": "Excelente",
        "zonas_danadas": [],
        "nota":
            "Modelo no disponible. "
            "Resultado simulado."
    }