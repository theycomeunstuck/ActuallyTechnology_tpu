import os
from PIL import Image
from collections import Counter
import random

# Папка с датасетом
dataset_path = "C:\\Users\\name\\Desktop\\images"   # например: dataset/PC, dataset/laptop, dataset/phone
output_path = "C:\\Users\\name\\Desktop\\images\\resized"

os.makedirs(output_path, exist_ok=True)

# Словари для статистики
class_counts = {}
file_formats = Counter()
image_sizes = Counter()

# Перебор классов
for class_name in os.listdir(dataset_path):
    class_folder = os.path.join(dataset_path, class_name)
    if not os.path.isdir(class_folder):
        continue

    images = [f for f in os.listdir(class_folder)
              if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"))]

    # Если больше 5 изображений – случайно выбираем 5
    selected = random.sample(images, 15) if len(images) > 100 else images


    # Считаем количество
    class_counts[class_name] = len(selected)

    # Создаём папку для класса в output
    out_class_folder = os.path.join(output_path, class_name)
    os.makedirs(out_class_folder, exist_ok=True)

    for img_name in selected:
        img_path = os.path.join(class_folder, img_name)
        try:
            img = Image.open(img_path)
            file_formats[img.format] += 1
            image_sizes[img.size] += 1

            # Приведение к 128x128
            img_resized = img.resize((128, 128))
            img_resized.save(os.path.join(out_class_folder, img_name))
        except Exception as e:
            print(f"[ERROR] {img_name}: {e}")

# Вывод отчета
print("\n--- Отчет ---")
print("Список классов:", list(class_counts.keys()))
print("Количество изображений в каждом классе:", class_counts)
print("Форматы файлов:", file_formats)
print("Размеры изображений:", image_sizes)
