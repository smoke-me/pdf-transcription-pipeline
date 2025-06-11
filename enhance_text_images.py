import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import threading
import time
import glob
from pathlib import Path
import argparse


def calculate_safe_thread_counts():
    cpu_count = os.cpu_count() or 1
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    total_memory_gb = psutil.virtual_memory().total / (1024**3)

    estimated_memory_per_thread_mb = 80
    memory_reserved_gb = min(1.0, total_memory_gb * 0.15)
    usable_memory_gb = available_memory_gb - memory_reserved_gb

    if usable_memory_gb < 0.5:
        process_threads = 1
    else:
        memory_based_threads = int(
            (usable_memory_gb * 1024) / estimated_memory_per_thread_mb)
        cpu_based_threads = max(2, min(cpu_count - 1, cpu_count * 3 // 4))
        process_threads = max(
            2, min(memory_based_threads, cpu_based_threads, 12))

    if process_threads > cpu_count:
        process_threads = cpu_count

    max_system_threads = threading.active_count() + 100
    process_threads = min(process_threads, max_system_threads // 2)

    process_threads = max(1, process_threads)

    return process_threads


def list_directories(directory):
    directories = []
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                directories.append(item)
        return sorted(directories)
    except Exception as e:
        print("Error")
        return []


def pick_directory(directories):
    if len(directories) == 0:
        sys.exit(0)
    elif len(directories) == 1:
        return directories[0]
    else:
        for idx, dirname in enumerate(directories, 1):
            print(f"{idx}: {dirname}")
        while True:
            try:
                choice = int(input("Select directory: "))
                if 1 <= choice <= len(directories):
                    return directories[choice - 1]
            except ValueError:
                pass
            print("Invalid")


def get_image_files(directory):
    image_extensions = [
        '*.jpg',
        '*.jpeg',
        '*.png',
        '*.bmp',
        '*.tiff',
        '*.tif',
        '*.webp']
    image_files = []

    for ext in image_extensions:
        pattern = os.path.join(directory, ext)
        image_files.extend(glob.glob(pattern, recursive=False))
        pattern_upper = os.path.join(directory, ext.upper())
        image_files.extend(glob.glob(pattern_upper, recursive=False))

    image_files = sorted(list(set(image_files)))
    return image_files


def get_unique_name(base_path):
    if not os.path.exists(base_path):
        return base_path

    counter = 1
    while True:
        new_path = f"{base_path}_{counter}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def enhance_text_image(image_path, output_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False, f"Could not read image: {image_path}"

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)

        gamma = 1.2
        gamma_corrected = np.power(denoised / 255.0, gamma) * 255.0
        gamma_corrected = np.uint8(gamma_corrected)

        blurred = cv2.GaussianBlur(gamma_corrected, (3, 3), 1.0)
        unsharp_strength = 0.5
        sharpened = cv2.addWeighted(
            gamma_corrected, 1.0 + unsharp_strength, blurred, -unsharp_strength, 0)

        pil_image = Image.fromarray(sharpened)

        contrast_enhancer = ImageEnhance.Contrast(pil_image)
        final_image = contrast_enhancer.enhance(1.1)

        final_image.save(output_path, quality=95, optimize=True)

        return True, None

    except Exception as e:
        return False, str(e)


def process_image_task(args):
    image_path, output_path, image_index = args
    success, error = enhance_text_image(image_path, output_path)
    return image_index, os.path.basename(image_path), success, error


def process_images_parallel(image_files, output_dir, process_threads):
    total_images = len(image_files)

    tasks = []
    for i, image_path in enumerate(image_files, 1):
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_dir, filename)
        tasks.append((image_path, output_path, i))

    processed_count = 0
    failed_images = []

    with ThreadPoolExecutor(max_workers=process_threads) as executor:
        future_to_task = {
            executor.submit(
                process_image_task,
                task): task for task in tasks}

        for future in as_completed(future_to_task):
            image_index, filename, success, error = future.result()

            if success:
                processed_count += 1
            else:
                failed_images.append((filename, error))

    if failed_images:
        pass
        print(f"Failed: {len(failed_images)}")

    return processed_count


def main():
    parser = argparse.ArgumentParser(description="Enhance images in a directory for better text recognition.")
    parser.add_argument("image_directory", nargs='?', default=None, help="Directory containing images to enhance. If not provided, prompts for selection.")
    args = parser.parse_args()

    process_threads = calculate_safe_thread_counts()
    
    target_directory = args.image_directory
    
    if target_directory and not os.path.isdir(target_directory):
        print(f"Error: Directory not found at {target_directory}")
        sys.exit(1)

    if not target_directory:
        current_directory = os.getcwd()
        directories = list_directories(current_directory)
        if not directories:
            print("No subdirectories found to process.")
            sys.exit(0)
        selected_dir = pick_directory(directories)
        target_directory = os.path.join(current_directory, selected_dir)

    image_files = get_image_files(target_directory)

    if not image_files:
        print(f"No image files found in {target_directory}")
        sys.exit(1)

    dir_basename = os.path.basename(target_directory.rstrip(os.sep))
    base_output_dir = os.path.join(
        os.path.dirname(target_directory),
        f"{dir_basename}_enhanced")
    output_dir = get_unique_name(base_output_dir)
    os.makedirs(output_dir, exist_ok=True)

    try:
        start_time = time.time()
        processed_images = process_images_parallel(
            image_files, output_dir, process_threads)
        end_time = time.time()

        processing_time = end_time - start_time

    except Exception as e:
        print("Error")
        sys.exit(1)


if __name__ == "__main__":
    main()
