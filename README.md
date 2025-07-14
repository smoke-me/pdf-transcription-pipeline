# PDF Transcription Pipeline

A Python-based automated pipeline for converting PDF documents to enhanced text transcriptions using computer vision and AI.

## Features

- PDF to image conversion with optimized DPI settings
- Image enhancement for improved text recognition
- AI-powered transcription using OpenAI's vision models
- Parallel processing for efficient batch operations
- Automatic cleanup of intermediate files
- Cross-platform compatibility

## Requirements

- Python 3.8+
- OpenAI API key
- System dependencies (see below)

## Dependencies Overview

This project requires both system-level and Python dependencies:

### System Dependencies (Required)

**Poppler** - PDF rendering library required for `pdf2image`
- **Critical**: Must be installed before Python dependencies
- Used by: `pdf_to_images.py`

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install poppler (required for PDF to image conversion)
brew install poppler
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

#### CentOS/RHEL/Fedora
```bash
sudo yum install poppler-utils  # CentOS/RHEL
# or
sudo dnf install poppler-utils  # Fedora
```

#### Windows
```bash
# Install using conda
conda install -c conda-forge poppler

# Or download and install from: https://poppler.freedesktop.org/
```

### Python Dependencies (Detailed)

**Core Processing:**
- `pdf2image>=1.16.0` - PDF to image conversion (`pdf_to_images.py`)
- `opencv-python>=4.8.0` - Image enhancement (`enhance_text_images.py`)
- `Pillow>=10.0.0` - Image processing (`enhance_text_images.py`)
- `numpy>=1.24.0` - Numerical operations (`enhance_text_images.py`)

**AI/API:**
- `openai>=1.0.0` - OpenAI API client (`transcribe_images.py`)
- `tiktoken>=0.4.0` - Token counting for OpenAI models

**System Management:**
- `psutil>=5.9.0` - System resource monitoring (all processing scripts)
- `python-dotenv>=1.0.0` - Environment variable loading (`transcribe_images.py`)

**Development/Build:**
- `setuptools>=68.0.0` - Python packaging tools
- `PyYAML>=6.0.0` - YAML configuration support
- `click>=7.0` - Command-line interface framework

**Built-in Modules Used:**
- `os`, `sys`, `time`, `threading`, `subprocess`, `signal`, `argparse`
- `glob`, `pathlib`, `shutil`, `venv`, `base64`, `select`

### Dependency Installation Order

1. **System dependencies first** (poppler)
2. **Virtual environment** (recommended)
3. **Python dependencies** via pip

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-transcription-pipeline.git
cd pdf-transcription-pipeline
```

2. **Install system dependencies first** (see System Dependencies section above)

3. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

5. Create environment configuration:
```bash
cp .env.example .env
```

6. Add your OpenAI API key to `.env`:
```
OPENAI_API_KEY=your_api_key_here
```

7. Create a prompt file:
```bash
echo "Transcribe all text from this image accurately, preserving formatting and structure." > prompt.txt
```

8. Test the installation:
```bash
python3 run_pipeline.py --help
```

9. **Optional**: Test individual components:
```bash
# Test PDF to images conversion
python3 pdf_to_images.py sample.pdf

# Test image enhancement  
python3 enhance_text_images.py sample_images/

# Test transcription (requires .env with OpenAI API key)
python3 transcribe_images.py sample_images_enhanced/

# Test text combination
python3 combine_text_files.py sample_images_enhanced_transcriptions/
```

**Note**: If you encounter silent failures, ensure all system dependencies are properly installed. The pipeline requires `poppler` to be available in your system PATH. Use the individual component tests above to isolate any issues.

## Usage

### Basic Usage
```bash
python run_pipeline.py document.pdf
```

### Keep Intermediate Files
```bash
python run_pipeline.py --keep document.pdf
```

### Interactive Mode
```bash
python run_pipeline.py
```

## Pipeline Components

| Script | Purpose |
|--------|---------|
| `run_pipeline.py` | Main orchestrator and entry point |
| `pdf_to_images.py` | Converts PDF pages to high-quality images |
| `enhance_text_images.py` | Applies image processing for text clarity |
| `transcribe_images.py` | Uses OpenAI API for text extraction |
| `combine_text_files.py` | Merges individual transcriptions |

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for transcription service
- `OPENAI_MODEL`: Optional. Sets the OpenAI model for transcription (e.g., `gpt-4.1-mini`, `gpt-4o`). Defaults to `gpt-4.1-mini`.

### Custom Prompts
Modify `prompt.txt` to customize transcription behavior and output format.

## Performance

The pipeline automatically optimizes thread counts based on:
- Available system memory
- CPU core count
- Current system load

## Output

Generated files:
- `transcription.txt`: Final combined transcription
- `*_images/`: PDF page images (removed unless `--keep` flag used)
- `*_enhanced/`: Enhanced images (removed unless `--keep` flag used)
- `*_transcriptions/`: Individual page transcriptions (removed unless `--keep` flag used)

## Error Handling

- Automatic retry logic for API failures
- Graceful degradation for corrupted images
- Comprehensive error logging
- Safe cleanup on interruption

## Troubleshooting

### Common Issues

#### "Unable to get page count. Is poppler installed and in PATH?"
**Solution**: Install poppler system dependency (see Dependencies Overview section)
- This is the most common issue - poppler must be installed at system level
- Verify installation: `pdftoppm -h` should work in terminal

#### "ModuleNotFoundError" for various packages
**Solution**: Install missing dependencies based on the specific module:
```bash
# For OpenCV errors (enhance_text_images.py)
pip install opencv-python numpy

# For OpenAI API errors (transcribe_images.py) 
pip install openai tiktoken python-dotenv

# For general dependency conflicts
pip install setuptools PyYAML click
```

#### ImportError: "No module named 'cv2'"
**Solution**: Install OpenCV for Python:
```bash
pip install opencv-python
# Or if you need contrib modules:
pip install opencv-contrib-python
```

#### "Could not read image" or PIL errors
**Solution**: Ensure Pillow is properly installed:
```bash
pip install --upgrade Pillow
```

#### Python dependency conflicts
**Solution**: Use a virtual environment to isolate dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### "NotADirectoryError: [Errno 20] Not a directory: 'python'"
**Solution**: This occurs when `python` command is not available. Use `python3` instead or create an alias:
```bash
# Temporary fix
alias python=python3

# Or run with python3 directly
python3 run_pipeline.py document.pdf
```

#### Virtual environment setup fails
**Solution**: Ensure Python venv module is available:
```bash
# macOS/Linux
python3 -m pip install --user virtualenv

# Then create environment
python3 -m virtualenv venv
```

#### OpenAI API errors
**Solution**: 
1. Verify your API key is correct in `.env`
2. Check your OpenAI account has available credits
3. Ensure you have access to the vision models

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.

## Version

Current version: 1.0.0 