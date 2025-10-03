import os
from PIL import Image
from collections import Counter
import random
from torchvision.transforms import v2
import torch.utils
import torchvision
import skimage as ski
import numpy as np



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


dataset_path = "dataset\\"
output_path = "dataset\\lb3"

os.makedirs(dataset_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

i = 1
dontBruteFolders = ["augmentation", "lb3"]
lastClassName = ""
# Перебор классов
for class_name in os.listdir(dataset_path):
    class_folder = os.path.join(dataset_path, class_name)
    if not os.path.isdir(class_folder) or class_name.lower() in dontBruteFolders: continue
    path = os.path.join(class_folder, "train")
    save_class_folder = os.path.join(output_path, class_name)
    os.makedirs(save_class_folder, exist_ok=True)

    for _imagePath in os.listdir(path):
        if random.randint(0, 5) >= 4  and lastClassName != class_name:
            i+=1

            image_path = os.path.join(path, _imagePath)
            img = Image.open(image_path).convert("RGB")  # L - grayscale
            name, ext = os.path.splitext(_imagePath)

            gray_transform = v2.Grayscale(num_output_channels=1)

            gray_img = gray_transform(img)
            saveFile(gray_img, _imagePath, save_class_folder, operType="grayScale")


            gray_np = np.array(gray_img)

            blurred = ski.filters.gaussian(gray_np, sigma=1)  # гауссово размытие
            saveFile(blurred, _imagePath, save_class_folder, operType="blurred")

            sharp_img = ski.filters.unsharp_mask(gray_np, radius=1, amount=1) #резкость
            saveFile(sharp_img, _imagePath, save_class_folder, operType="sharpen")

            edges = ski.filters.sobel(gray_np)  # оператор Собеля (контур более чёткий - через градиент считает)
            saveFile(edges, _imagePath, save_class_folder, operType="edges")

            blurredEdges = ski.filters.sobel(blurred)  #
            saveFile(blurredEdges, _imagePath, save_class_folder, operType="blurredEdges")



            gray_img_T = v2.ToTensor()(gray_np)
            binImg = (gray_img_T > 0.5).float() * 255#pytorch
            saveFile(binImg, _imagePath, save_class_folder, operType="binaryThreshold")

            thresh = ski.filters.threshold_otsu(gray_np) #otsu method
            binImg = (gray_np > thresh).astype("uint8") * 255
            saveFile(binImg, _imagePath, save_class_folder, operType="otsu")

            lastClassName = class_name




