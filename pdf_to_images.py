import os
import sys
import glob
from pdf2image import convert_from_path

def list_pdf_files(directory):
    pdf_files = []
    for ext in ['*.pdf', '*.PDF']:
        pdf_files.extend(glob.glob(os.path.join(directory, ext)))
    return sorted([os.path.basename(f) for f in pdf_files])

def pick_pdf(pdf_files):
    if len(pdf_files) == 0:
        print("No PDFs found")
        sys.exit(1)
    elif len(pdf_files) == 1:
        return pdf_files[0]
    else:
        for idx, fname in enumerate(pdf_files, 1):
            print(f"{idx}: {fname}")
        while True:
            try:
                choice = int(input("Select PDF: "))
                if 1 <= choice <= len(pdf_files):
                    return pdf_files[choice - 1]
            except ValueError:
                pass
            print("Invalid")

def get_unique_name(base_path):
    if not os.path.exists(base_path):
        return base_path
    counter = 1
    while True:
        new_path = f"{base_path}_{counter}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def convert_pdf_to_images(pdf_path, output_dir):
    try:
        images = convert_from_path(pdf_path, dpi=200)
        for i, image in enumerate(images, 1):
            output_path = os.path.join(output_dir, f"{i}.jpg")
            image.save(output_path, 'JPEG', quality=95, optimize=True)
        return len(images)
    except Exception as e:
        print(f"Error: {e}")
        return 0

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    directory = os.getcwd()
    
    if arg:
        if os.path.isfile(arg) and arg.lower().endswith('.pdf'):
            pdf_file = arg
        else:
            print("Invalid PDF file")
            sys.exit(1)
    else:
        pdf_files = list_pdf_files(directory)
        pdf_file = os.path.join(directory, pick_pdf(pdf_files))
    
    pdf_basename = os.path.splitext(os.path.basename(pdf_file))[0]
    base_output_dir = os.path.join(os.path.dirname(pdf_file), f"{pdf_basename}_images")
    output_dir = get_unique_name(base_output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    processed_pages = convert_pdf_to_images(pdf_file, output_dir)
    
    if processed_pages > 0:
        print(f"Converted {processed_pages} pages")
    else:
        print("Failed to convert PDF")
        sys.exit(1)

if __name__ == "__main__":
    main() 