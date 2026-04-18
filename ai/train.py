"""
Script de entrenamiento de EvaluaPlus con Anomalib
=====================================================
Este script:
1. Descarga el dataset de madera desde Roboflow
2. Prepara las imágenes en la estructura que Anomalib necesita
3. Entrena el modelo PatchCore
4. Guarda el modelo entrenado en /model/

Uso:
    pip install anomalib roboflow opencv-python
    python train.py --api_key TU_API_KEY
"""

import os
import shutil
import argparse
from pathlib import Path


def descargar_dataset(api_key: str, destino: str = "dataset_raw"):
    """Descarga el dataset de madera desde Roboflow."""
    from roboflow import Roboflow

    print("📥 Descargando dataset de madera desde Roboflow...")
    rf = Roboflow(api_key=api_key)

    # Dataset de defectos en madera con licencia CC BY 4.0
    project = rf.workspace("woodsample").project("wood-defect-dataset_seg")
    dataset = project.version(1).download("folder", location=destino)

    print(f"✅ Dataset descargado en: {destino}")
    return destino


def preparar_dataset(dataset_raw: str, dataset_listo: str = "dataset_anomalib"):
    """
    Convierte el dataset al formato que Anomalib necesita:

    dataset_anomalib/
    ├── train/
    │   └── good/       ← imágenes SIN defectos
    └── test/
        ├── good/       ← imágenes SIN defectos (para validación)
        └── defect/     ← imágenes CON defectos
    """
    print("🔧 Preparando estructura de dataset para Anomalib...")

    # Crear carpetas
    for split in ["train/good", "test/good", "test/defect"]:
        Path(f"{dataset_listo}/{split}").mkdir(parents=True, exist_ok=True)

    extensiones = {".jpg", ".jpeg", ".png"}

    # Buscar imágenes en el dataset descargado
    raw_path = Path(dataset_raw)
    todas_imagenes = []
    for ext in extensiones:
        todas_imagenes.extend(raw_path.rglob(f"*{ext}"))

    if not todas_imagenes:
        print("❌ No se encontraron imágenes. Verifica la ruta del dataset.")
        return None

    print(f"📸 Total de imágenes encontradas: {len(todas_imagenes)}")

    # Separar imágenes con y sin defectos
    # Las imágenes con anotaciones (.txt o .json) tienen defectos
    imagenes_con_defecto = []
    imagenes_sin_defecto = []

    for img_path in todas_imagenes:
        anotacion = img_path.with_suffix(".txt")
        tiene_defecto = anotacion.exists() and anotacion.stat().st_size > 0
        if tiene_defecto:
            imagenes_con_defecto.append(img_path)
        else:
            imagenes_sin_defecto.append(img_path)

    print(f"  ✅ Sin defecto: {len(imagenes_sin_defecto)}")
    print(f"  ❌ Con defecto: {len(imagenes_con_defecto)}")

    # Si no hay suficientes sin defecto, usar todas para train/good
    if len(imagenes_sin_defecto) < 10:
        print("⚠️  Pocas imágenes sin defecto. Usando todas las imágenes como good para entrenar.")
        imagenes_sin_defecto = todas_imagenes
        imagenes_con_defecto = []

    # 80% para entrenamiento, 20% para prueba
    split = int(len(imagenes_sin_defecto) * 0.8)
    train_good = imagenes_sin_defecto[:split]
    test_good = imagenes_sin_defecto[split:]

    # Copiar imágenes
    for i, img in enumerate(train_good):
        shutil.copy(img, f"{dataset_listo}/train/good/{i:04d}{img.suffix}")

    for i, img in enumerate(test_good):
        shutil.copy(img, f"{dataset_listo}/test/good/{i:04d}{img.suffix}")

    for i, img in enumerate(imagenes_con_defecto):
        shutil.copy(img, f"{dataset_listo}/test/defect/{i:04d}{img.suffix}")

    print(f"✅ Dataset preparado en: {dataset_listo}")
    print(f"   Train/good: {len(train_good)} imágenes")
    print(f"   Test/good:  {len(test_good)} imágenes")
    print(f"   Test/defect:{len(imagenes_con_defecto)} imágenes")

    return dataset_listo


def entrenar_modelo(dataset_path: str, modelo_salida: str = "model"):
    """Entrena el modelo PatchCore de Anomalib."""
    print("🧠 Iniciando entrenamiento con PatchCore...")

    from anomalib.data import Folder
    from anomalib.models import Patchcore
    from anomalib.engine import Engine

    Path(modelo_salida).mkdir(exist_ok=True)

    # Configurar dataset
    datamodule = Folder(
        name="madera",
        root=dataset_path,
        normal_dir="train/good",
        abnormal_dir="test/defect",
        normal_test_dir="test/good",
        image_size=(256, 256),
        train_batch_size=16,
        eval_batch_size=8,
    )

    # Configurar modelo PatchCore
    model = Patchcore(
        backbone="wide_resnet50_2",
        layers_list=["layer2", "layer3"],
        coreset_sampling_ratio=0.1,
        num_neighbors=9,
    )

    # Entrenar
    engine = Engine(
        max_epochs=1,  # PatchCore no necesita épocas, aprende en 1 paso
        accelerator="auto",
        devices=1,
        default_root_dir=modelo_salida,
    )

    engine.fit(model=model, datamodule=datamodule)

    print("✅ Entrenamiento completado.")

    # Exportar modelo
    print("💾 Exportando modelo...")
    engine.export(
        model=model,
        export_type="torch",
        export_root=modelo_salida,
    )

    print(f"✅ Modelo guardado en: {modelo_salida}/")
    print("\n🎉 ¡Listo! Copia la carpeta 'model/' dentro de 'ai/' en tu proyecto.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrenar modelo EvaluaPlus")
    parser.add_argument("--api_key", required=True, help="Tu API key de Roboflow")
    parser.add_argument("--skip_download", action="store_true", help="Saltar descarga si ya tienes el dataset")
    args = parser.parse_args()

    # Paso 1: Descargar dataset
    if not args.skip_download:
        descargar_dataset(args.api_key)
    else:
        print("⏭️  Saltando descarga del dataset...")

    # Paso 2: Preparar estructura
    dataset_listo = preparar_dataset("dataset_raw")
    if dataset_listo is None:
        exit(1)

    # Paso 3: Entrenar
    entrenar_modelo(dataset_listo)