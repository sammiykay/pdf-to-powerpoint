import io
import re
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

def extract_title_from_pdf(pdf_file):
    """
    Extract the title from the first page of a PDF file using OCR.
    
    Args:
        pdf_file: PDF file as a BytesIO object
        
    Returns:
        Extracted title as a string
    """
    try:
        # Convert first page of PDF to image
        images = convert_from_bytes(pdf_file.read(), first_page=1, last_page=1)
        pdf_file.seek(0)  # Reset file pointer
        
        if not images:
            return None
        
        # Process the first page image with OCR
        first_page = images[0]
        
        # Process the page with OCR
        text = pytesseract.image_to_data(first_page, output_type=pytesseract.Output.DICT)
        
        # Combine OCR data
        lines = []
        current_line = []
        current_line_number = 0
        
        for i in range(len(text['text'])):
            if text['text'][i].strip():  # Skip empty strings
                # If we have a new line number, save the previous line and start a new one
                if text['line_num'][i] != current_line_number and current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                
                current_line_number = text['line_num'][i]
                current_line.append(text['text'][i])
                
        # Add the last line if it exists
        if current_line:
            lines.append(' '.join(current_line))
        
        # Look for potential title candidates (large font, bold)
        title_candidates = []
        
        for i in range(len(text['text'])):
            if text['text'][i].strip() and text['conf'][i] > 50:  # Skip low confidence
                # Look for text with larger font or bold text (higher height)
                if text['height'][i] > 15:  # Adjust threshold based on your PDFs
                    title_candidates.append({
                        'text': text['text'][i],
                        'font_size': text['height'][i],
                        'line_num': text['line_num'][i],
                        'conf': text['conf'][i],
                        'top': text['top'][i]
                    })
        
        # Sort candidates by position (top first)
        title_candidates.sort(key=lambda x: x['top'])
        
        # Find full lines with these candidates
        potential_titles = []
        
        for candidate in title_candidates:
            # Find the complete line containing this candidate
            line_text = next((line for line in lines if candidate['text'] in line), candidate['text'])
            
            # Skip if it matches common non-title text patterns
            if re.search(r'Gartner.*Usage Policy|Copyright|Confidential|Page \d+', line_text, re.IGNORECASE):
                continue
                
            potential_titles.append({
                'text': line_text,
                'font_size': candidate['font_size'],
                'top': candidate['top'],
                'conf': candidate['conf']
            })
        
        # Remove duplicates
        unique_titles = []
        for pt in potential_titles:
            if pt['text'] not in [ut['text'] for ut in unique_titles]:
                unique_titles.append(pt)
        
        # If we have candidates, return the first one (topmost prominent text)
        if unique_titles:
            return unique_titles[0]['text'].strip()
        
        # Fallback: try to find the first non-empty, non-header/footer line
        for line in lines:
            line = line.strip()
            if line and not re.search(r'Gartner.*Usage Policy|Copyright|Confidential|Page \d+', line, re.IGNORECASE):
                return line
        
        return None
    except Exception as e:
        print(f"Error extracting title: {str(e)}")
        return None

def extract_text_from_pdf_page(pdf_file, page_num):
    """
    Extract text from a specific page of a PDF file using OCR.
    
    Args:
        pdf_file: PDF file as a BytesIO object
        page_num: Page number to extract text from (1-based)
        
    Returns:
        Extracted text as a string
    """
    try:
        # Convert PDF page to image
        images = convert_from_bytes(pdf_file.read(), first_page=page_num, last_page=page_num)
        pdf_file.seek(0)  # Reset file pointer
        
        if not images:
            return ""
        
        # Process the page image with OCR
        page_image = images[0]
        text = pytesseract.image_to_string(page_image)
        
        return text
    except Exception as e:
        print(f"Error extracting text from page {page_num}: {str(e)}")
        return ""
