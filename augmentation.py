import os
from PIL import Image
from collections import Counter
import random
from torchvision.transforms import v2

dataset_path = "dataset\\"
output_path = "dataset\\augmentation"

os.makedirs(dataset_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)


# Перебор классов
for class_name in os.lisяtdir(dataset_path):
    class_folder = os.path.join(dataset_path, class_name)
    if not os.path.isdir(class_folder) or class_name == "augmentation": continue
    path = os.path.join(class_folder, "train")

    save_class_folder = os.path.join(output_path, class_name)
    os.makedirs(save_class_folder, exist_ok=True)

    for image in os.listdir(path):

        img = Image.open(os.path.join(path, image)).convert("RGB")
        for i in range(3):

            transform = v2.Compose([
                v2.RandomHorizontalFlip(p=0.5),
                v2.RandomVerticalFlip(p=0.15),
                v2.RandomApply([v2.RandomRotation(degrees=25)], p=0.7),
                v2.RandomGrayscale(p=0.3),
                v2.GaussianBlur(kernel_size=(3, 3), sigma=(0.1, 2.5)),
                # v2.Resize((224, 224)),
                v2.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
                v2.RandomPerspective(distortion_scale=0.5, p=0.5),

                ])
            aug_img = transform(img)
            name, ext = os.path.splitext(image)
            save_path = os.path.join(save_class_folder, f"{name}_{i}{ext}")
            aug_img.save(save_path)




