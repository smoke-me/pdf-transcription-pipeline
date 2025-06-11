import os
import sys
import time
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import threading


def calculate_safe_thread_counts():

    cpu_count = os.cpu_count() or 1
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    total_memory_gb = psutil.virtual_memory().total / (1024**3)

    estimated_memory_per_thread_mb = 30

    memory_reserved_gb = min(0.5, total_memory_gb * 0.1)
    usable_memory_gb = available_memory_gb - memory_reserved_gb

    if usable_memory_gb < 0.3:
        file_threads = 2
    else:

        memory_based_threads = int(
            (usable_memory_gb * 1024) / estimated_memory_per_thread_mb)

        cpu_based_threads = max(2, min(cpu_count, cpu_count + 4))

        file_threads = max(2, min(memory_based_threads, cpu_based_threads, 8))

    if file_threads > cpu_count * 2:
        file_threads = cpu_count * 2

    max_system_threads = threading.active_count() + 50
    file_threads = min(file_threads, max_system_threads // 3)

    file_threads = max(1, file_threads)

    return file_threads


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


def natural_sort_key(filepath):
    import re
    filename = os.path.basename(filepath)

    parts = re.split(r'(\d+)', filename)

    for i in range(len(parts)):
        if parts[i].isdigit():
            parts[i] = int(parts[i])
    return parts


def get_text_files(directory):
    text_extensions = ['*.txt']
    text_files = []

    for ext in text_extensions:
        pattern = os.path.join(directory, ext)
        text_files.extend(glob.glob(pattern, recursive=False))

        pattern_upper = os.path.join(directory, ext.upper())
        text_files.extend(glob.glob(pattern_upper, recursive=False))

    text_files = sorted(list(set(text_files)), key=natural_sort_key)
    return text_files


def calculate_total_file_size(text_files):
    total_size = 0
    for file_path in text_files:
        try:
            total_size += os.path.getsize(file_path)
        except OSError:
            continue
    return total_size


def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return file_path, content, True, None
    except Exception as e:
        return file_path, None, False, str(e)


def read_file_task(args):
    file_path, file_index = args
    return file_index, read_file_content(file_path)


def combine_files_parallel(text_files, file_threads):
    total_files = len(text_files)

    tasks = []
    for i, file_path in enumerate(text_files):
        tasks.append((file_path, i))

    read_count = 0
    failed_files = []
    file_contents = [None] * total_files

    unit = "file",

    with ThreadPoolExecutor(max_workers=file_threads) as executor:
        future_to_task = {
            executor.submit(
                read_file_task,
                task): task for task in tasks}

        for future in as_completed(future_to_task):
            file_index, (file_path, content, success, error) = future.result()
            filename = os.path.basename(file_path)

            if success:
                file_contents[file_index] = content
                read_count += 1
            else:
                failed_files.append((filename, error))
                file_contents[file_index] = f"\n[ERROR: Could not read {filename}: {error}]\n"

    if failed_files:
        print(f"Failed: {len(failed_files)}")

    combined_content = ""

    for i, (file_path, content) in enumerate(zip(text_files, file_contents)):
        filename = os.path.basename(file_path)

        if i > 0:
            combined_content += "\n"

        if content:
            cleaned_content = content.strip()
            if cleaned_content:
                combined_content += cleaned_content + "\n"
        else:
            combined_content += f"[ERROR: No content available for {filename}]\n"

    return combined_content, read_count, failed_files


def combine_files_simple(text_files):
    total_files = len(text_files)

    combined_content = ""
    read_count = 0
    failed_files = []

    for i, file_path in enumerate(text_files):
        filename = os.path.basename(file_path)

        if i > 0:
            combined_content += "\n"

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            combined_content += content
            if not content.endswith('\n'):
                combined_content += "\n"
            read_count += 1

        except Exception as e:
            error_msg = f"[ERROR: Could not read {filename}: {str(e)}]\n"
            combined_content += error_msg
            failed_files.append((filename, str(e)))

    return combined_content, read_count, failed_files


def get_unique_name(base_path):
    if not os.path.exists(base_path):
        return base_path

    counter = 1
    while True:
        name, ext = os.path.splitext(base_path)
        new_path = f"{name}_{counter}{ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    current_directory = os.getcwd()
    target_directory = None

    if arg:
        if os.path.isdir(arg):
            target_directory = os.path.abspath(arg)
        else:
        print("Invalid")
        sys.exit(1)

    if not target_directory:
        directories = list_directories(current_directory)
        selected_dir = pick_directory(directories)
        target_directory = os.path.join(current_directory, selected_dir)

    text_files = get_text_files(target_directory)

    if not text_files:
        sys.exit(1)

    total_size_bytes = calculate_total_file_size(text_files)
    total_size_mb = total_size_bytes / (1024 * 1024)

    USE_PARALLEL_THRESHOLD_MB = 1.0

    if total_size_mb >= USE_PARALLEL_THRESHOLD_MB:
        file_threads = calculate_safe_thread_counts()

        start_time = time.time()
        combined_content, read_count, failed_files = combine_files_parallel(
            text_files, file_threads)
        end_time = time.time()
    else:
        start_time = time.time()
        combined_content, read_count, failed_files = combine_files_simple(
            text_files)
        end_time = time.time()

    script_directory = os.path.dirname(os.path.abspath(__file__))
    base_output_path = os.path.join(script_directory, "transcription.txt")
    output_path = get_unique_name(base_output_path)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(combined_content)

        processing_time = end_time - start_time

        if failed_files:
        print(f"Failed: {len(failed_files)}")

    except Exception as e:
        print("Error")
        sys.exit(1)


if __name__ == "__main__":
    main()
