import os
import torch.utils
import torchvision
import random
import glob
import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple


def saveFile(image, _imagePath, save_class_folder, operType="E_"):
    name, ext = os.path.splitext(_imagePath)
    save_path = os.path.join(save_class_folder, f"{operType}_{name}_{i}{ext}")

    if isinstance(image, Image.Image):
        image.save(save_path)
    elif isinstance(image, np.ndarray):
        # Если это numpy.ndarray (float или uint8)
        if image.dtype != np.uint8:
            # Если float [0..1], приводим к uint8
            image = (image * 255).astype(np.uint8)
        Image.fromarray(image).save(save_path)
    elif isinstance(image, torch.Tensor):

        # Обычно тензор [C,H,W] или [1,H,W], значения [0,1]
        if image.dim() == 3 and image.shape[0] in [1, 3]:
            torchvision.utils.save_image(image, save_path)
        elif image.dim() == 2:
            image = image.unsqueeze(0) # [H,W] → [1,H,W]
            torchvision.utils.save_image(image, save_path)

    else:
        raise ValueError(f"Неподдержимая форма тензора: {image.shape}")


def _to_gray(img):
    if img is None:
        raise ValueError("img is None")
    if img.ndim == 2:
        return img
    if img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    raise ValueError(f"Unexpected shape: {img.shape}")


def cannyOutlineDetecion(img, _imagePath, save_class_folder):
    #метод считает градиент изменения яркости (оператор Собеля)
    cfgs = [(50, 150), (100, 200), (150, 250)] #нижний и верхний порог. если сила градиента < X, then it`s not контур. if grad > X, thats a outline
    for t1, t2 in cfgs:
        edges = cv2.Canny(img, t1, t2)
        name, ext = os.path.splitext(_imagePath)
        out = os.path.join(save_class_folder, f"Canny_{t1}-{t2}_{name}_{i}.{ext}")
        cv2.imwrite(out, edges)

    # Слишком маленькие значения → будет куча шумных линий.
    # Слишком большие → пропадут настоящие границы.


def harrisCornerDetection(img, _imagePath, save_class_folder):
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    h = cv2.cornerHarris(np.float32(gray), blockSize=3, ksize=3, k=0.04)
    h = cv2.dilate(h, None)
    th = 0.01 * h.max()  # порог 1%
    corners_harris = np.argwhere(h > th)  # (y, x)

    # делаем копию картинки для отрисовки. не умеем рисовать точки на массиве
    vis = img.copy() if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for y, x in corners_harris:  # порядок argwhere — (y, x)
        cv2.circle(vis, (int(x), int(y)), 1, (0, 210, 255), -1) #BGR

    name, ext = os.path.splitext(_imagePath)
    out = os.path.join(save_class_folder, f"Harris_{name}{ext if ext else '.png'}")
    cv2.imwrite(out, vis)


def shiTomasi(img, _imagePath, save_class_folder, maxCorners=50, qualityLevel=0.01, minDistance=10, blockSize=3):
    if img is None:
        raise ValueError("img is None")

    # серый
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # сглаживание (ВАЖНО: размываем gray, не img)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Shi–Tomasi
    corners = cv2.goodFeaturesToTrack(
        gray,
        maxCorners=maxCorners,
        qualityLevel=qualityLevel,
        minDistance=minDistance,
        blockSize=blockSize
    )

    # делаем 3-канальную картинку для цветных точек
    vis = img.copy() if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    if corners is not None:
        for x, y in corners.reshape(-1, 2):
            cv2.circle(vis, (int(x), int(y)), 2, (0, 0, 255), -1)  # маленькие красные точки

    # сохраняем
    name, ext = os.path.splitext(os.path.basename(_imagePath))
    out = os.path.join(save_class_folder, f"ShiTomasi_{name}{ext if ext else '.png'}")
    cv2.imwrite(out, vis)
    return out


def siftFeatures(img, _imagePath, save_class_folder, nfeatures=0):
    os.makedirs(save_class_folder, exist_ok=True)
    gray = _to_gray(img)
    sift = cv2.SIFT_create(nfeatures=nfeatures)
    keypoints, descriptors = sift.detectAndCompute(gray, None)

    vis = cv2.drawKeypoints(img if img.ndim==3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR),
                            keypoints, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    name, ext = os.path.splitext(os.path.basename(_imagePath))
    out = os.path.join(save_class_folder, f"SIFT_{name}{ext if ext else '.png'}")
    cv2.imwrite(out, vis)
    return keypoints, descriptors


def orbFeatures(img, _imagePath, save_class_folder):
    """
    Рисует ключевые точки ORB и сохраняет картинку. Возвращает (keypoints, descriptors).
    """
    os.makedirs(save_class_folder, exist_ok=True)
    gray = _to_gray(img)
    orb = cv2.ORB_create()
    keypoints, descriptors = orb.detectAndCompute(gray, None)


    vis = cv2.drawKeypoints(img if img.ndim==3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR),
                            keypoints, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    name, ext = os.path.splitext(os.path.basename(_imagePath))
    out = os.path.join(save_class_folder, f"ORB_{name}{ext if ext else '.png'}")
    cv2.imwrite(out, vis)
    return keypoints, descriptors


def matchFeatures(img1, _imagePath1, img2, _imagePath2, save_class_folder,
                  method="ORB", keep=60, ratio=0.75):
    #Строит совпадения между двумя изображениями и сохраняет визуализацию.
    #method: "ORB" или "SIFT"

    os.makedirs(save_class_folder, exist_ok=True)
    gray1, gray2 = _to_gray(img1), _to_gray(img2)

    if method.upper() == "SIFT":
        extractor = cv2.SIFT_create()
        norm = cv2.NORM_L2
    else:
        extractor = cv2.ORB_create()
        norm = cv2.NORM_HAMMING

    kp1, des1 = extractor.detectAndCompute(gray1, None)
    kp2, des2 = extractor.detectAndCompute(gray2, None)
    if des1 is None or des2 is None or len(kp1)==0 or len(kp2)==0:
        raise ValueError("Нет дескрипторов/ключевых точек для матчинга")

    # KNN + ratio test (надёжнее, чем crossCheck)
    bf = cv2.BFMatcher(norm)
    knn = bf.knnMatch(des1, des2, k=2)
    good = []
    for m, n in knn:
        if m.distance < ratio * n.distance:
            good.append(m)

    # чуть отсортируем и ограничим
    good = sorted(good, key=lambda x: x.distance)[:keep]

    vis = cv2.drawMatches(
        img1 if img1.ndim==3 else cv2.cvtColor(img1, cv2.COLOR_GRAY2BGR),
        kp1,
        img2 if img2.ndim==3 else cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR),
        kp2,
        good, None,
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
    )

    base1 = os.path.splitext(os.path.basename(_imagePath1))[0]
    base2 = os.path.splitext(os.path.basename(_imagePath2))[0]
    out = os.path.join(save_class_folder, f"MATCH_{method.upper()}_{base1}_vs_{base2}.png")
    cv2.imwrite(out, vis)
    return good, out

dataset_path = "dataset\\"
output_path = "dataset\\lb4"

os.makedirs(dataset_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

i = 1
dontBruteFolders = ["augmentation", "lb3", "lb4", "lb5", "lb"]
lastClassName = ""


for class_name in os.listdir(dataset_path):
    class_folder = os.path.join(dataset_path, class_name)
    if not os.path.isdir(class_folder) or class_name.lower() in dontBruteFolders:
        continue

    path = os.path.join(class_folder, "train")
    save_class_folder = os.path.join(output_path, class_name)
    os.makedirs(save_class_folder, exist_ok=True)

    for _imagePath in os.listdir(path):
        if random.randint(0, 5) >= 4 and lastClassName != class_name:
            i += 1
            image_path = os.path.join(path, _imagePath)

            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"[WARN] Не удалось открыть: {image_path}")
                continue


            cannyOutlineDetecion(img, _imagePath, save_class_folder)
            harrisCornerDetection(img, _imagePath, save_class_folder)
            shiTomasi(img, _imagePath, save_class_folder)


            lastClassName = class_name


img1 = cv2.imread("dataset/phone/train/662d9256fa0ae3c7956edcb5f066f87b819051e4.jpg")
img2 = cv2.imread("dataset/phone/train/apple-iphone-17-pro.jpg")
save_dir = "_out"

# ORB. как-то плохо (даже ужасно) отрабатывает, но работает
kp1, d1 = orbFeatures(img1, "img/a.jpg", save_dir)
kp2, d2 = orbFeatures(img2, "img/b.jpg", save_dir)
matches, out_path = matchFeatures(img1, "img/a.jpg", img2, "img/b.jpg", save_dir, method="ORB", keep=80)

# SIFT
kp1, d1 = siftFeatures(img1, "img/a.jpg", save_dir)
kp2, d2 = siftFeatures(img2, "img/b.jpg", save_dir)
matches, out_path = matchFeatures(img1, "img/a.jpg", img2, "img/b.jpg", save_dir, method="SIFT", keep=80)
