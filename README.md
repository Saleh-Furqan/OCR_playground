# OCR Receipt Processor

Simple receipt processing system that converts receipt images into standardized JSON format using OCR and AI.

## Features

- 🔍 **Traditional OCR** - Tesseract-based text extraction with multiple preprocessing methods
- 🤖 **AI Structuring** - Groq-powered receipt parsing into standardized JSON
- 📱 **Web Interface** - Simple upload and view interface
- 🏪 **Store Agnostic** - Processes receipts from any store

## Project Structure

```
OCR_playground/
├── src/
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── enhanced_ocr.py    # Multi-engine OCR processing  
│   │   ├── ocr_processor.py   # Main OCR processor
│   │   └── receipt_schema.py  # Data models and schemas
│   ├── llm/
│   │   ├── grok_enhancer.py   # Groq API integration for receipt structuring
│   │   ├── llm_enhancer.py    # Legacy LLM enhancement (optional)
│   │   ├── llm_providers.py   # LLM provider support
│   │   └── vision_providers.py # Cloud vision APIs (optional)
│   └── web/
│       ├── app.py             # Flask web application
│       └── templates/         # HTML templates
├── data/                      # Sample images
├── uploads/                   # Temporary upload directory
├── .env                       # Environment variables
├── requirements.txt           # Python dependencies
├── run.py                     # Command line tool
├── webapp.py                  # Web application entry point
└── README.md
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd OCR_playground
   ```

2. **Install system dependencies**
   ```bash
   sudo apt update
   sudo apt install -y tesseract-ocr tesseract-ocr-eng python3-pip
   ```

3. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**
   ```bash
   # Edit .env with your API key
   echo "GROQ_API_KEY=your_groq_api_key_here" > .env
   ```

## Configuration

The `.env` file contains:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key from: https://console.groq.com/

## Usage

### Web Interface (Recommended)

1. **Start the web application**
   ```bash
   source venv/bin/activate
   python webapp.py
   ```

2. **Access the interface**
   - Open browser to `http://localhost:5000`
   - Upload a receipt image
   - View the structured JSON receipt

### Command Line

```bash
source venv/bin/activate
python run.py path/to/receipt.jpg
```

## How It Works

### Simple 2-Step Process

1. **OCR Extraction** 
   - Traditional Tesseract OCR with multiple preprocessing methods
   - Image enhancement (denoising, rotation correction, contrast adjustment)
   - Confidence-based result selection

2. **AI Structuring**
   - Groq API parses OCR text into standardized JSON format
   - Extracts: merchant, items, prices, totals, dates, etc.
   - Returns structured data for easy processing

### OCR Processing Details

- **Image preprocessing**: 7 different enhancement methods
- **Multiple Tesseract configs**: Different PSM modes for various receipt layouts  
- **Confidence scoring**: Selects best result based on receipt characteristics
- **Automatic rotation detection**: Handles tilted receipt images

## Output Format

```json
{
  "merchant_name": "WALMART SUPERCENTER",
  "merchant_address": "123 Main St, City, State",
  "transaction_date": "2024-01-15",
  "transaction_time": "14:30",
  "items": [
    {
      "name": "BANANAS",
      "quantity": 2,
      "unit_price": 1.29,
      "total_price": 2.58
    }
  ],
  "subtotal": 12.45,
  "tax_amount": 1.12,
  "total_amount": 13.57,
  "payment_method": "card",
  "receipt_number": "12345"
}
```

## API Usage

### Process Receipt Endpoint

```bash
curl -X POST http://localhost:5000/upload \
  -F "receipt=@/path/to/receipt.jpg"
```

Returns a redirect to the structured receipt view.

## Dependencies

- **tesseract-ocr** - OCR engine
- **opencv-python** - Image processing
- **pillow** - Image handling
- **flask** - Web framework
- **requests** - HTTP client for Groq API
- **python-dotenv** - Environment variable management

## Troubleshooting

### Tesseract Not Found
```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Groq API Errors
- Check your API key in `.env`
- Verify internet connection
- Check Groq API status at https://status.groq.com/

### Poor OCR Results
- Ensure receipt image is well-lit and in focus
- Try straightening tilted images
- Higher resolution images work better

