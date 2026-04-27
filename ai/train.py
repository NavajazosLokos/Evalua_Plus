"""
Script de entrenamiento de EvaluaPlus con Anomalib
=====================================================
Uso:
    py train.py --api_key TU_API_KEY
"""

import os
import shutil
import argparse
from pathlib import Path


def descargar_dataset(api_key: str, destino: str = "dataset_raw"):
    from roboflow import Roboflow

    print("📥 Descargando dataset de madera desde Roboflow...")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace("faron-ace-fs10i").project("wood-defect-instant")
    versions = project.versions()
    version_num = versions[0].version if versions else 1
    print(f"📦 Usando versión: {version_num}")
    project.version(version_num).download("yolov8", location=destino)
    print(f"✅ Dataset descargado en: {destino}")
    return destino


def preparar_dataset(dataset_raw: str, dataset_listo: str = "dataset_anomalib"):
    """
    YOLOv8 tiene esta estructura:
        dataset_raw/
        ├── train/
        │   ├── images/
        │   └── labels/
        ├── valid/
        │   ├── images/
        │   └── labels/
        └── test/
            ├── images/
            └── labels/

    Anomalib necesita:
        dataset_anomalib/
        ├── train/good/     <- imágenes sin defecto
        └── test/
            ├── good/       <- imágenes sin defecto
            └── defect/     <- imágenes con defecto
    """
    print("🔧 Preparando estructura de dataset para Anomalib...")

    for split in ["train/good", "test/good", "test/defect"]:
        Path(f"{dataset_listo}/{split}").mkdir(parents=True, exist_ok=True)

    raw_path = Path(dataset_raw)
    extensiones = {".jpg", ".jpeg", ".png"}

    def tiene_defecto(img_path):
        # En YOLOv8, las etiquetas están en la carpeta 'labels' al mismo nivel que 'images'
        label_path = Path(str(img_path).replace("images", "labels")).with_suffix(".txt")
        return label_path.exists() and label_path.stat().st_size > 0

    # Procesar train
    train_images = []
    for ext in extensiones:
        train_images.extend((raw_path / "train" / "images").rglob(f"*{ext}"))

    train_good = [img for img in train_images if not tiene_defecto(img)]
    train_defect = [img for img in train_images if tiene_defecto(img)]

    # Procesar valid y test para el conjunto de prueba
    test_images = []
    for split_name in ["valid", "test"]:
        split_path = raw_path / split_name / "images"
        if split_path.exists():
            for ext in extensiones:
                test_images.extend(split_path.rglob(f"*{ext}"))

    test_good = [img for img in test_images if not tiene_defecto(img)]
    test_defect = [img for img in test_images if tiene_defecto(img)]

    print(f"  Train - ✅ good: {len(train_good)}  ❌ defect: {len(train_defect)}")
    print(f"  Test  - ✅ good: {len(test_good)}   ❌ defect: {len(test_defect)}")

    # Copiar imágenes
    for i, img in enumerate(train_good):
        shutil.copy(img, f"{dataset_listo}/train/good/{i:04d}{img.suffix}")
    for i, img in enumerate(test_good):
        shutil.copy(img, f"{dataset_listo}/test/good/{i:04d}{img.suffix}")
    for i, img in enumerate(test_defect + train_defect):
        shutil.copy(img, f"{dataset_listo}/test/defect/{i:04d}{img.suffix}")

    total_good = len(train_good)
    total_defect = len(test_defect) + len(train_defect)

    if total_good < 10:
        print("⚠️  Pocas imágenes good. Usando todas las imágenes como good.")
        all_imgs = list(raw_path.rglob("*.jpg")) + list(raw_path.rglob("*.png"))
        split = int(len(all_imgs) * 0.8)
        for i, img in enumerate(all_imgs[:split]):
            shutil.copy(img, f"{dataset_listo}/train/good/{i:04d}{img.suffix}")
        for i, img in enumerate(all_imgs[split:]):
            shutil.copy(img, f"{dataset_listo}/test/good/{i:04d}{img.suffix}")

    print(f"✅ Dataset preparado en: {dataset_listo}")
    return dataset_listo


def entrenar_modelo(dataset_path: str, modelo_salida: str = "model"):
    print("🧠 Iniciando entrenamiento con PatchCore...")

    from anomalib.data import Folder
    from anomalib.models import Patchcore
    from anomalib.engine import Engine

    Path(modelo_salida).mkdir(exist_ok=True)

    datamodule = Folder(
        name="madera",
        root=dataset_path,
        normal_dir="train/good",
        abnormal_dir="test/defect",
        normal_test_dir="test/good",
        train_batch_size=16,
        eval_batch_size=8,
        num_workers=0,
    )

    model = Patchcore(
        backbone="wide_resnet50_2",
        layers=["layer2", "layer3"],
        coreset_sampling_ratio=0.1,
        num_neighbors=9,
    )

    engine = Engine(
        max_epochs=1,
        accelerator="auto",
        devices=1,
        default_root_dir=modelo_salida,
    )

    engine.fit(model=model, datamodule=datamodule)
    print("✅ Entrenamiento completado.")

    print("💾 Exportando modelo...")
    engine.export(
        model=model,
        export_type="torch",
        export_root=modelo_salida,
    )

    print(f"✅ Modelo guardado en: {modelo_salida}/")
    print("\n🎉 ¡Listo! Copia la carpeta 'model/' dentro de 'ai/' en tu proyecto.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--skip_download", action="store_true")
    parser.add_argument("--skip_prepare", action="store_true")
    args = parser.parse_args()

    if not args.skip_download:
        descargar_dataset(args.api_key)

    if not args.skip_prepare:
        dataset_listo = preparar_dataset("dataset_raw")
    else:
        dataset_listo = "dataset_anomalib"

    if dataset_listo:
        entrenar_modelo(dataset_listo)