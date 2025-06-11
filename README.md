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
- Required system dependencies for PDF processing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-transcription-pipeline.git
cd pdf-transcription-pipeline
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create environment configuration:
```bash
cp .env.example .env
```

4. Add your OpenAI API key to `.env`:
```
OPENAI_API_KEY=your_api_key_here
```

5. Create a prompt file:
```bash
echo "Transcribe all text from this image accurately, preserving formatting and structure." > prompt.txt
```

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