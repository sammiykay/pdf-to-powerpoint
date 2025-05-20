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
        Extracted title as a string (complete sentence)
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
        
        # Combine OCR data into lines
        lines = []
        current_line = []
        current_line_number = 0
        
        for i in range(len(text['text'])):
            if text['text'][i].strip():  # Skip empty strings
                # If we have a new line number, save the previous line and start a new one
                if text['line_num'][i] != current_line_number and current_line:
                    lines.append({
                        'text': ' '.join(current_line),
                        'line_num': current_line_number,
                        'font_size': max([text['height'][j] for j in range(len(text['text'])) 
                                         if text['line_num'][j] == current_line_number and text['text'][j].strip()]),
                        'top': min([text['top'][j] for j in range(len(text['text'])) 
                                   if text['line_num'][j] == current_line_number and text['text'][j].strip()]),
                        'conf': sum([text['conf'][j] for j in range(len(text['text'])) 
                                    if text['line_num'][j] == current_line_number and text['text'][j].strip()]) / 
                               len([j for j in range(len(text['text'])) 
                                   if text['line_num'][j] == current_line_number and text['text'][j].strip()])
                    })
                    current_line = []
                
                current_line_number = text['line_num'][i]
                current_line.append(text['text'][i])
        
        # Add the last line if it exists
        if current_line:
            lines.append({
                'text': ' '.join(current_line),
                'line_num': current_line_number,
                'font_size': max([text['height'][j] for j in range(len(text['text'])) 
                                 if text['line_num'][j] == current_line_number and text['text'][j].strip()]),
                'top': min([text['top'][j] for j in range(len(text['text'])) 
                           if text['line_num'][j] == current_line_number and text['text'][j].strip()]),
                'conf': sum([text['conf'][j] for j in range(len(text['text'])) 
                            if text['line_num'][j] == current_line_number and text['text'][j].strip()]) / 
                       len([j for j in range(len(text['text'])) 
                           if text['line_num'][j] == current_line_number and text['text'][j].strip()])
            })
        
        # Filter out lines that match common non-title patterns
        filtered_lines = [line for line in lines 
                         if not re.search(r'Gartner.*Usage Policy|Copyright|Confidential|Page \d+', 
                                         line['text'], re.IGNORECASE)]
        
        # Sort lines by font size (descending) and position (top first)
        # This prioritizes larger text that appears earlier in the document
        potential_titles = sorted(filtered_lines, key=lambda x: (-x['font_size'], x['top']))
        
        # Extract complete sentences by combining adjacent lines with similar font sizes
        title_sentences = []
        
        if potential_titles:
            # Start with the most prominent line
            current_sentence = [potential_titles[0]]
            current_font_size = potential_titles[0]['font_size']
            
            # Combine adjacent lines with similar font size
            for i in range(1, len(potential_titles)):
                line = potential_titles[i]
                # If the line is close to the previous one and has similar font size
                if (abs(line['top'] - current_sentence[-1]['top']) < 30 and 
                    abs(line['font_size'] - current_font_size) < 5):
                    current_sentence.append(line)
                else:
                    # If we have a complete sentence, add it to our results
                    if current_sentence:
                        combined_text = ' '.join([l['text'] for l in current_sentence])
                        if len(combined_text.split()) >= 3:  # Ensure it's a meaningful sentence
                            title_sentences.append({
                                'text': combined_text,
                                'font_size': current_font_size,
                                'top': current_sentence[0]['top']
                            })
                    
                    # Start a new sentence
                    current_sentence = [line]
                    current_font_size = line['font_size']
            
            # Add the last sentence if it exists
            if current_sentence:
                combined_text = ' '.join([l['text'] for l in current_sentence])
                if len(combined_text.split()) >= 3:  # Ensure it's a meaningful sentence
                    title_sentences.append({
                        'text': combined_text,
                        'font_size': current_font_size,
                        'top': current_sentence[0]['top']
                    })
        
        # If we have sentence candidates, return the one with the largest font
        if title_sentences:
            title_sentences.sort(key=lambda x: (-x['font_size'], x['top']))
            return title_sentences[0]['text'].strip()
        
        # If no complete sentences were found, fall back to the original algorithm
        if potential_titles:
            return potential_titles[0]['text'].strip()
        
        # Final fallback: use any non-empty line
        for line in lines:
            if line['text'].strip():
                return line['text'].strip()
        
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
