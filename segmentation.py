import os
import torch.utils
import torchvision
import random
import glob
import cv2

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans



def binarySegm(name, ext, img, OUT_DIR):
    # 2) Выбираем порог T в диапазоне [0..255]
    T = 127

    # 3) Пороговая сегментация: пиксели >= T -> 255, иначе -> 0
    _, binary = cv2.threshold(img, T, 255, cv2.THRESH_BINARY)

    # 4) Сохраняем результат
    cv2.imwrite(os.path.join(OUT_DIR, f"{name}_binary_fixed_.{ext}"), binary)

def otsu(name, ext, img, OUT_DIR):
    # Немного сгладим шум, чтобы Отсу работал стабильнее
    img_blur = cv2.GaussianBlur(img, (5, 5), 0)

    # THRESH_BINARY + OTSU игнорирует переданный порог и подбирает свой
    T, binary_otsu = cv2.threshold(img_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    print(f"Порог Отсу: {T:.2f}")
    cv2.imwrite(os.path.join(OUT_DIR, f"{name}_otsu.{ext}"), binary_otsu)


def kmeans(img_path, OUT_DIR, k=3):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

    h, w, c = img.shape

    X = img.reshape(-1, 3)
    name, ext = img_path.split("/")[-1].split(".")

    # Запускаем k-means
    kmeans = KMeans(
        n_clusters=k,  # число кластеров (например, 3)
        init="k-means++",  # умная инициализация
        n_init=10,  # сколько запусков с разными начальными центрами
        # random_state=42
    )
    labels = kmeans.fit_predict(X)
    centers = kmeans.cluster_centers_.astype(np.uint8)

    # Визуализация: заменяем каждый пиксель на цвет центра своего кластера
    segmented = centers[labels].reshape(h, w, c)

    cv2.imwrite(os.path.join(OUT_DIR, f"{name}_{k}Kmeans.{ext}"), segmented)

def kmeans(img_path: str, OUT_DIR: str, k: int = 3, mode: str = "color"):
    """
    K-means сегментация изображения.

    :param img_path: путь к файлу изображения
    :param k: количество кластеров
    :param mode: "color" (по умолчанию) или "gray"
    """
    if mode == "color":
        img = cv2.imread(img_path)  # BGR
        if img is None:
            raise FileNotFoundError(f"Не найден файл {img_path}")
        h, w, c = img.shape
        X = img.reshape(-1, 3)  # 3 признака: B,G,R

    elif mode == "gray":
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Не найден файл {img_path}")
        h, w = img.shape
        c = 1
        X = img.reshape(-1, 1)  # 1 признак: яркость

    else:
        raise ValueError("mode должен быть 'color' или 'gray'")

    # Запускаем KMeans
    kmeans = KMeans(
        n_clusters=k,
        init="k-means++",
        n_init=10,
        random_state=42
    )
    labels = kmeans.fit_predict(X)
    centers = kmeans.cluster_centers_.astype(np.uint8)

    # Восстанавливаем картинку
    segmented = centers[labels].reshape(h, w, c)
    if mode == "gray":
        segmented = segmented.reshape(h, w)  # убрать лишнее измерение

    # Имя файла
    base = os.path.splitext(os.path.basename(img_path))[0]
    out_name = f"{base}_kmeans_{mode}_{k}.png"

    cv2.imwrite(os.path.join(OUT_DIR, out_name), segmented)

def apply_watershed(path, cv_gray, OUT_DIR):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cv_gray = clahe.apply(cv_gray)

    cv_img = cv2.imread(path, cv2.IMREAD_COLOR)
    name, ext = path.split("/")[-1].split(".")

    # Препроцессинг — бинаризация для маркеров
    ret, thresh = cv2.threshold(cv_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Определяем фон и объекты через морфологию
    kernel = np.ones((3,3), np.uint8)
    sure_bg = cv2.dilate(thresh, kernel, iterations=5)
    dist_transform = cv2.distanceTransform(thresh, cv2.DIST_L2, 5)
    ret, sure_fg = cv2.threshold(dist_transform, 0.3 * dist_transform.max(), 255, 0)
    sure_fg = np.uint8(sure_fg)
    unknown = cv2.subtract(sure_bg, sure_fg)

    # Маркеры
    ret, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0

    # Применяем watershed
    cv_bgr = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
    ws_img = cv_bgr.copy()
    cv2.watershed(ws_img, markers)
    ws_img[markers == -1] = [0,0,255]
    cv2.imwrite(os.path.join(OUT_DIR, f"{name}_watershed.{ext}"), ws_img)
    return ws_img



def main(path):
    name, ext = path.split("/")[-1].split(".")


    OUT_DIR = f"_out/_segm/{name}"
    os.makedirs(OUT_DIR, exist_ok=True)


    # 1) Загружаем изображение и переводим в оттенки серого
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Не найден файл {path}")

    img = cv2.GaussianBlur(img, (5, 5), 0)
    binarySegm(name, ext, img.copy(), OUT_DIR)
    otsu(name, ext, img.copy(), OUT_DIR)
    apply_watershed(path, img.copy(), OUT_DIR)
    for k in range(2, 5):
        kmeans(img_path=path, k=k, mode="color", OUT_DIR=OUT_DIR)
        kmeans(img_path=path, k=k, mode="gray", OUT_DIR=OUT_DIR)


if __name__ == "__main__":
    _path  = [
        'dataset/phone/train/662d9256fa0ae3c7956edcb5f066f87b819051e4.jpg',
        'dataset/phone/train/apple-iphone-17-pro.jpg',
        'dataset/pc/train/1916363_1432132451746.png',
        'dataset/laptop/test/2022-06-06T190356Z_765158456_RC2IMU9YR922_RTRMADP_3_APPLE-DEVELOPER_0.jpg',
    ]

    for path in _path:
        main(path)


