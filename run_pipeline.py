import os
import sys
import time
import subprocess
import threading
import signal
import argparse
import glob
from pathlib import Path
import shutil
import venv

def get_unique_name(base_path):
    if not os.path.exists(base_path):
        return base_path
    counter = 1
    while True:
        if os.path.isfile(base_path) or base_path.endswith('.txt'):
            name, ext = os.path.splitext(base_path)
            new_path = f"{name}_{counter}{ext}"
        else:
            new_path = f"{base_path}_{counter}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def get_python_executable():
    for python_cmd in ['python', 'python3']:
        try:
            result = subprocess.run([python_cmd, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return python_cmd
        except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError):
            continue
    return None

def setup_environment():
    venv_path = os.path.join(os.getcwd(), 'venv')
    if not os.path.exists(venv_path):
        try:
            venv.create(venv_path, with_pip=True)
        except Exception:
            return False
    
    python_cmd = get_python_executable()
    if not python_cmd:
        return False
    
    if os.name == 'nt':
        pip_path = os.path.join(venv_path, 'Scripts', 'pip')
        python_path = os.path.join(venv_path, 'Scripts', 'python')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        python_path = os.path.join(venv_path, 'bin', 'python')
    
    if os.path.exists('requirements.txt'):
        try:
            subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], 
                         capture_output=True, timeout=300)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    return python_path

class PipelineManager:
    def __init__(self, keep_directories=False, python_executable='python'):
        self.keep_directories = keep_directories
        self.python_executable = python_executable
        self.created_directories = []
        self.current_process = None
        self.cancelled = False
        self.force_quit = False
        self.key_listener_thread = None
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.start_key_listener()

    def signal_handler(self, signum, frame):
        self.cancel_pipeline()

    def start_key_listener(self):
        def listen_for_keys():
            try:
                import select
                import sys
                while not self.cancelled and not self.force_quit:
                    if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == 'x':
                            self.cancel_pipeline()
                            break
                        elif key == 'c':
                            self.force_quit = True
                            os._exit(1)
            except ImportError:
                pass
            except Exception:
                pass
        self.key_listener_thread = threading.Thread(target=listen_for_keys, daemon=True)
        self.key_listener_thread.start()

    def cancel_pipeline(self):
        self.cancelled = True
        if self.current_process:
            try:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()
            except Exception:
                pass
        self.cleanup_directories()
        sys.exit(0)

    def cleanup_directories(self):
        if self.keep_directories:
            return
        if not self.created_directories:
            return
        for directory in self.created_directories:
            try:
                if os.path.exists(directory):
                    shutil.rmtree(directory)
            except Exception:
                pass
        venv_path = os.path.join(os.getcwd(), 'venv')
        try:
            if os.path.exists(venv_path):
                shutil.rmtree(venv_path)
        except Exception:
            pass

    def find_pdf_files(self, directory):
        pdf_files = []
        for ext in ['*.pdf', '*.PDF']:
            pdf_files.extend(glob.glob(os.path.join(directory, ext)))
        unique_files = sorted(list(set([os.path.basename(f) for f in pdf_files])))
        return unique_files

    def select_pdf_with_timeout(self, pdf_files, timeout=60):
        if len(pdf_files) == 0:
            return None
        elif len(pdf_files) == 1:
            return pdf_files[0]
        else:
            for idx, fname in enumerate(pdf_files, 1):
                print(f"{idx}: {fname}")
            start_time = time.time()
            selected = None

            def timeout_checker():
                nonlocal selected
                time.sleep(timeout)
                if selected is None:
                    selected = "TIMEOUT"

            timeout_thread = threading.Thread(target=timeout_checker, daemon=True)
            timeout_thread.start()

            while selected is None and not self.cancelled and not self.force_quit:
                try:
                    if time.time() - start_time > timeout:
                        return None
                    choice_input = input("Select PDF: ")
                    choice = int(choice_input)
                    if 1 <= choice <= len(pdf_files):
                        selected = pdf_files[choice - 1]
                        break
                    else:
                        print("Invalid")
                except ValueError:
                    print("Invalid")
                except (EOFError, KeyboardInterrupt):
                    return None

            if selected == "TIMEOUT":
                return None
            return selected

    def run_script(self, script_name, args, description):
        if self.cancelled or self.force_quit:
            return False, None
        try:
            cmd = [self.python_executable, script_name] + args
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            output_lines = []
            while True:
                if self.cancelled or self.force_quit:
                    self.current_process.terminate()
                    return False, None
                output = self.current_process.stdout.readline()
                if output == '' and self.current_process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    output_lines.append(line)
            return_code = self.current_process.poll()
            if return_code == 0:
                return True, output_lines
            else:
                return False, output_lines
        except Exception:
            return False, None
        finally:
            self.current_process = None

    def find_actual_directory(self, base_dir, pattern):
        if os.path.exists(base_dir):
            return base_dir
        parent_dir = os.path.dirname(base_dir)
        base_name = os.path.basename(base_dir)
        for item in os.listdir(parent_dir):
            if item.startswith(base_name + "_") and item[len(base_name)+1:].isdigit():
                full_path = os.path.join(parent_dir, item)
                if os.path.isdir(full_path):
                    return full_path
        return base_dir

    def find_transcription_file(self):
        base_path = os.path.join(os.getcwd(), "transcription.txt")
        if os.path.exists(base_path):
            return base_path
        for file in os.listdir(os.getcwd()):
            if file.startswith("transcription_") and file.endswith(".txt"):
                middle = file[13:-4]
                if middle.isdigit():
                    return os.path.join(os.getcwd(), file)
        return base_path

    def run_pipeline(self, pdf_path):
        if self.cancelled or self.force_quit:
            return False
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        pdf_dir = os.path.dirname(os.path.abspath(pdf_path))

        base_images_dir = os.path.join(pdf_dir, f"{pdf_name}_images")
        success, output = self.run_script('pdf_to_images.py', [pdf_path], "PDF to Images")
        if not success:
            return False

        images_dir = self.find_actual_directory(base_images_dir, f"{pdf_name}_images")
        if os.path.exists(images_dir):
            self.created_directories.append(images_dir)

        base_enhanced_dir = os.path.join(pdf_dir, f"{os.path.basename(images_dir)}_enhanced")
        success, output = self.run_script('enhance_text_images.py', [images_dir], "Enhance Images")
        if not success:
            return False

        enhanced_dir = self.find_actual_directory(base_enhanced_dir, f"{os.path.basename(images_dir)}_enhanced")
        if os.path.exists(enhanced_dir):
            self.created_directories.append(enhanced_dir)

        base_transcriptions_dir = os.path.join(pdf_dir, f"{os.path.basename(enhanced_dir)}_transcriptions")
        success, output = self.run_script('transcribe_images.py', [enhanced_dir], "Transcribe Images")
        if not success:
            return False

        transcriptions_dir = self.find_actual_directory(base_transcriptions_dir, f"{os.path.basename(enhanced_dir)}_transcriptions")
        if os.path.exists(transcriptions_dir):
            self.created_directories.append(transcriptions_dir)

        success, output = self.run_script('combine_text_files.py', [transcriptions_dir], "Combine Text")
        if not success:
            return False

        transcription_file = self.find_transcription_file()
        if os.path.exists(transcription_file):
            return True
        else:
            print("Not found")
            return False

def show_help():
    pass

def main():
    parser = argparse.ArgumentParser(
        description="Run the full PDF to text transcription pipeline.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('pdf_file', nargs='?', default=None, help='Path to the PDF file to process.\nIf not provided, the script scans the current directory for PDFs.')
    parser.add_argument('--keep', action='store_true', help='Keep intermediate directories.')
    args = parser.parse_args()

    python_executable = setup_environment()
    if not python_executable:
        print("Failed to set up Python virtual environment.")
        sys.exit(1)

    pipeline = PipelineManager(keep_directories=args.keep, python_executable=python_executable)

    try:
        pdf_path = args.pdf_file

        if pdf_path:
            if not (os.path.isfile(pdf_path) and pdf_path.lower().endswith('.pdf')):
                print(f"Error: Invalid PDF file path: {pdf_path}")
                sys.exit(1)
            pdf_path = os.path.abspath(pdf_path)
        else:
            current_dir = os.getcwd()
            pdf_files = pipeline.find_pdf_files(current_dir)
            if not pdf_files:
                print("No PDF files found in the current directory.")
                sys.exit(1)
            
            if os.environ.get("CI"):
                print("CI environment detected, selecting first PDF.")
                selected_pdf = pdf_files[0]
            else:
                selected_pdf = pipeline.select_pdf_with_timeout(pdf_files)

            if selected_pdf is None:
                print("No PDF selected or selection timed out.")
                sys.exit(1)
            pdf_path = os.path.join(current_dir, selected_pdf)

        required_scripts = ['pdf_to_images.py', 'enhance_text_images.py', 'transcribe_images.py', 'combine_text_files.py']
        missing_scripts = []

        for script in required_scripts:
            if not os.path.exists(script):
                missing_scripts.append(script)

        if missing_scripts:
            sys.exit(1)

        start_time = time.time()
        success = pipeline.run_pipeline(pdf_path)
        end_time = time.time()

        if success:
            total_time = end_time - start_time
            pipeline.cleanup_directories()
        else:
            pipeline.cleanup_directories()
            sys.exit(1)

    except KeyboardInterrupt:
        pipeline.cancel_pipeline()
    except Exception:
        pipeline.cleanup_directories()
        sys.exit(1)

if __name__ == "__main__":
    main() 