import os
import sys
import base64
import time
import glob
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import threading


def calculate_safe_thread_counts():
    cpu_count = os.cpu_count() or 1
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    total_memory_gb = psutil.virtual_memory().total / (1024**3)

    estimated_memory_per_thread_mb = 50
    memory_reserved_gb = min(1.0, total_memory_gb * 0.15)
    usable_memory_gb = available_memory_gb - memory_reserved_gb

    if usable_memory_gb < 0.5:
        api_threads = 2
    else:
        memory_based_threads = int(
            (usable_memory_gb * 1024) / estimated_memory_per_thread_mb)
        cpu_based_threads = max(4, min(cpu_count * 2, cpu_count + 8))
        api_threads = max(4, min(memory_based_threads, cpu_based_threads, 20))

    if api_threads > cpu_count * 3:
        api_threads = cpu_count * 3

    max_system_threads = threading.active_count() + 100
    api_threads = min(api_threads, max_system_threads // 2)
    api_threads = max(2, api_threads)

    return api_threads


def load_env():
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.getcwd(), '.env')
        if not os.path.exists(env_path):
            print(".env not found")
            sys.exit(1)

        success = load_dotenv(env_path)
        if not success:
            print("Failed to load .env")
            sys.exit(1)

    except ImportError:
        sys.exit(1)


def load_prompt():
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("prompt.txt not found")
        sys.exit(1)


def list_directories(directory):
    directories = []
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                directories.append(item)
        return sorted(directories)
    except Exception as e:
        print("Error:")
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


def natural_sort_key(filepath):
    import re
    filename = os.path.basename(filepath)
    parts = re.split(r'(\d+)', filename)
    for i in range(len(parts)):
        if parts[i].isdigit():
            parts[i] = int(parts[i])
    return parts


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

    image_files = sorted(list(set(image_files)), key=natural_sort_key)
    return image_files


def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        return None, str(e)


def transcribe_image_with_retry(client, prompt, image_path, max_retries=None):
    attempt = 0

    base64_image = encode_image_to_base64(image_path)
    if base64_image is None:
        return False, "Encode failed"

    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext in ['.jpg', '.jpeg']:
        media_type = 'image/jpeg'
    elif file_ext == '.png':
        media_type = 'image/png'
    elif file_ext == '.webp':
        media_type = 'image/webp'
    else:
        media_type = 'image/png'

    while True:
        attempt += 1
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0
            )

            transcription = response.choices[0].message.content

            lines = transcription.splitlines()
            cleaned_lines = []
            for line in lines:
                if line.strip() == '```':
                    continue
                cleaned_lines.append(line.replace('```', ''))
            transcription = '\n'.join(cleaned_lines)

            return True, transcription

        except Exception as e:
            if max_retries and attempt >= max_retries:
                return False, f"Max retries exceeded"

            time.sleep(5)


def transcribe_image_task(args):
    client, prompt, image_path, output_path, image_index = args
    filename = os.path.basename(image_path)

    success, result = transcribe_image_with_retry(client, prompt, image_path)

    if success:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            return image_index, filename, True, None
        except Exception as e:
            return image_index, filename, False, f"Save failed: {str(e)}"
    else:
        return image_index, filename, False, result


def process_images_parallel(
        image_files,
        output_dir,
        client,
        prompt,
        api_threads):
    total_images = len(image_files)

    tasks = []
    for i, image_path in enumerate(image_files, 1):
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}.txt"
        output_path = os.path.join(output_dir, output_filename)
        tasks.append((client, prompt, image_path, output_path, i))

    processed_count = 0
    failed_images = []

    with ThreadPoolExecutor(max_workers=api_threads) as executor:
        future_to_task = {
            executor.submit(
                transcribe_image_task,
                task): task for task in tasks}

        for future in as_completed(future_to_task):
            image_index, filename, success, error = future.result()

            if success:
                processed_count += 1
            else:
                failed_images.append((filename, error))

    if failed_images:
        pass

    return processed_count


def get_unique_name(base_path):
    if not os.path.exists(base_path):
        return base_path

    counter = 1
    while True:
        new_path = f"{base_path}_{counter}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def main():
    api_threads = calculate_safe_thread_counts()

    load_env()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    prompt = load_prompt()

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    current_directory = os.getcwd()
    target_directory = None

    if arg:
        if os.path.isdir(arg):
            target_directory = os.path.abspath(arg)
        else:
            print("Invalid directory")
            sys.exit(1)

    if not target_directory:
        directories = list_directories(current_directory)
        selected_dir = pick_directory(directories)
        target_directory = os.path.join(current_directory, selected_dir)

    image_files = get_image_files(target_directory)

    if not image_files:
        sys.exit(1)

    dir_basename = os.path.basename(target_directory.rstrip(os.sep))
    base_output_dir = os.path.join(
        os.path.dirname(target_directory),
        f"{dir_basename}_transcriptions")
    output_dir = get_unique_name(base_output_dir)
    os.makedirs(output_dir, exist_ok=True)

    try:
        start_time = time.time()
        processed_images = process_images_parallel(
            image_files, output_dir, client, prompt, api_threads)
        end_time = time.time()

        processing_time = end_time - start_time

    except Exception as e:
        print("Error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
