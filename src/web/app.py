#!/usr/bin/env python3

import os
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import json
import sys
from pathlib import Path

# Add src to path for imports
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from core.ocr_processor import OCRProcessor
from llm.grok_enhancer import GrokEnhancer
from core.config import config

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = str(config.UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Create upload directory
config.ensure_directories()

# Initialize processors
ocr_processor = OCRProcessor()
grok_enhancer = GrokEnhancer()

# Simple in-memory storage for receipts (replace with database later)
receipts_storage = {}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def get_or_create_device_id():
    """Get or create device ID from session"""
    if 'device_id' not in session:
        session['device_id'] = str(uuid.uuid4())
    return session['device_id']

@app.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Test route to verify app is working"""
    return jsonify({'status': 'OK', 'message': 'Flask app is running'})

@app.route('/upload', methods=['POST'])
def upload_receipt():
    """Handle receipt image upload and processing"""
    if 'receipt' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['receipt']
    
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload an image file.')
        return redirect(url_for('index'))
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Get device ID and assign to receipt
        device_id = get_or_create_device_id()
        
        # Extract text with OCR
        text, metadata = ocr_processor.extract_text(file_path)
        
        # Structure with Grok
        if grok_enhancer.is_available():
            structured_receipt = grok_enhancer.structure_receipt(text)
            receipt_id = str(uuid.uuid4())
            
            # Store receipt in memory
            receipts_storage[receipt_id] = {
                'structured': structured_receipt,
                'raw_text': text,
                'metadata': metadata
            }
        else:
            receipt_id = str(uuid.uuid4())
            receipts_storage[receipt_id] = {
                'error': 'Grok not configured',
                'raw_text': text,
                'metadata': metadata
            }
        
        # Clean up uploaded file
        os.remove(file_path)
        
        # Redirect to digital receipt display page
        return redirect(url_for('view_digital_receipt', receipt_id=receipt_id))
        
    except Exception as e:
        flash(f'Error processing receipt: {str(e)}')
        return redirect(url_for('index'))

@app.route('/receipt/<receipt_id>')
def view_receipt(receipt_id):
    """View a specific receipt by ID"""
    if receipt_id not in receipts_storage:
        flash('Receipt not found')
        return redirect(url_for('index'))
    
    receipt_data = receipts_storage[receipt_id]['raw_data']
    standardized = receipts_storage[receipt_id]['standardized']
    insights = receipts_storage[receipt_id].get('insights', {})
    
    return render_template('receipt_view.html', 
                         receipt=receipt_data, 
                         standardized=standardized,
                         insights=insights)

@app.route('/digital-receipt/<receipt_id>')
def view_digital_receipt(receipt_id):
    """View a digital receipt by ID"""
    if receipt_id not in receipts_storage:
        flash('Receipt not found')
        return redirect(url_for('index'))
    
    receipt_info = receipts_storage[receipt_id]
    
    return render_template('grok_receipt.html', 
                         structured_receipt=receipt_info.get('structured'),
                         raw_text=receipt_info.get('raw_text'),
                         metadata=receipt_info.get('metadata'),
                         error=receipt_info.get('error'))

@app.route('/ai-setup')
def ai_setup():
    """AI Setup page with API key instructions"""
    return render_template('llm_setup.html')

@app.route('/receipts')
def list_receipts():
    """List all receipts for current device"""
    device_id = get_or_create_device_id()
    user_receipts = []
    
    for receipt_id, data in receipts_storage.items():
        if data['raw_data'].device_id == device_id:
            user_receipts.append(data['standardized'])
    
    # Sort by processed time (newest first)
    user_receipts.sort(key=lambda x: x.processed_at, reverse=True)
    
    return render_template('receipt_list.html', receipts=user_receipts)

@app.route('/api/process', methods=['POST'])
def api_process_receipt():
    """API endpoint for receipt processing"""
    if 'receipt' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['receipt']
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400
    
    try:
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Process receipt
        receipt_data = ocr_processor.process_receipt(file_path)
        standardized = StandardizedReceipt.from_receipt_data(receipt_data)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        # Return JSON response
        return jsonify({
            'success': True,
            'data': standardized.model_dump(mode='json')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)