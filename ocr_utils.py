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
        Extracted title as a string (complete multi-line title)
    """
    try:
        # Convert first page of PDF to image with higher DPI for better OCR
        images = convert_from_bytes(pdf_file.read(), first_page=1, last_page=1, dpi=300)
        pdf_file.seek(0)  # Reset file pointer
        
        if not images:
            return None
        
        # Process the first page image with OCR
        first_page = images[0]
        
        # Use image_to_data for more detailed OCR information
        text = pytesseract.image_to_data(first_page, output_type=pytesseract.Output.DICT)
        
        # Combine OCR data into lines with more metadata
        lines = []
        current_line = []
        current_line_number = 0
        
        for i in range(len(text['text'])):
            if text['text'][i].strip():  # Skip empty strings
                # If we have a new line number, save the previous line and start a new one
                if text['line_num'][i] != current_line_number and current_line:
                    # Find all indices for this line
                    line_indices = [j for j in range(len(text['text'])) 
                                   if text['line_num'][j] == current_line_number and text['text'][j].strip()]
                    
                    lines.append({
                        'text': ' '.join(current_line),
                        'line_num': current_line_number,
                        'font_size': max([text['height'][j] for j in line_indices]),
                        'top': min([text['top'][j] for j in line_indices]),
                        'left': min([text['left'][j] for j in line_indices]),
                        'width': max([text['left'][j] + text['width'][j] for j in line_indices]) - 
                                min([text['left'][j] for j in line_indices]),
                        'conf': sum([text['conf'][j] for j in line_indices]) / len(line_indices)
                    })
                    current_line = []
                
                current_line_number = text['line_num'][i]
                current_line.append(text['text'][i])
        
        # Add the last line if it exists
        if current_line:
            # Find all indices for this line
            line_indices = [j for j in range(len(text['text'])) 
                           if text['line_num'][j] == current_line_number and text['text'][j].strip()]
            
            lines.append({
                'text': ' '.join(current_line),
                'line_num': current_line_number,
                'font_size': max([text['height'][j] for j in line_indices]),
                'top': min([text['top'][j] for j in line_indices]),
                'left': min([text['left'][j] for j in line_indices]),
                'width': max([text['left'][j] + text['width'][j] for j in line_indices]) - 
                        min([text['left'][j] for j in line_indices]),
                'conf': sum([text['conf'][j] for j in line_indices]) / len(line_indices)
            })
        
        # Filter out lines that match common non-title patterns
        filtered_lines = [line for line in lines 
                         if not re.search(r'Gartner.*Usage Policy|Copyright|Confidential|Page \d+|^\d+$', 
                                         line['text'], re.IGNORECASE)]
        
        # Group lines by similar font size and vertical position
        def group_lines_by_title():
            # Sort lines by vertical position (top first)
            sorted_lines = sorted(filtered_lines, key=lambda x: x['top'])
            
            # Identify the largest font size in the top section of the document
            top_section_lines = [line for line in sorted_lines if line['top'] < sorted_lines[0]['top'] + 300]
            if not top_section_lines:
                return None
                
            max_font_size = max([line['font_size'] for line in top_section_lines])
            
            # Find lines with font size close to max (at least one is a title line)
            title_font_threshold = max_font_size * 0.8  # Allow some variation
            potential_title_lines = [line for line in sorted_lines 
                                   if line['font_size'] >= title_font_threshold and
                                   line['top'] < sorted_lines[0]['top'] + 400]  # Look only in top section
            
            if not potential_title_lines:
                return None
                
            # Group adjacent lines with similar font size as a complete title
            title_groups = []
            current_group = [potential_title_lines[0]]
            
            for i in range(1, len(potential_title_lines)):
                current_line = potential_title_lines[i]
                prev_line = current_group[-1]
                
                # Check if lines are close and have similar font size
                if (current_line['top'] - (prev_line['top'] + prev_line['font_size']) < 20 and
                    abs(current_line['font_size'] - prev_line['font_size']) < 5):
                    current_group.append(current_line)
                else:
                    # If the current group has content, save it
                    if current_group:
                        title_groups.append(current_group)
                    # Start a new group
                    current_group = [current_line]
            
            # Add the last group
            if current_group:
                title_groups.append(current_group)
                
            return title_groups
            
        # Get grouped title lines
        title_groups = group_lines_by_title()
        
        if title_groups:
            # Sort groups by average font size (largest first)
            title_groups.sort(key=lambda group: -sum(line['font_size'] for line in group)/len(group))
            
            # Take the most prominent group and combine its lines
            main_title_group = title_groups[0]
            main_title_group.sort(key=lambda line: line['top'])  # Sort by vertical position
            
            full_title = ' '.join([line['text'] for line in main_title_group])
            
            # For Workshop-style titles, ensure we capture the full title by checking
            # if it starts with a workshop indicator followed by a colon
            if re.match(r'^(workshop|webinar|seminar|presentation):', full_title.lower()):
                return full_title
                
            # If the title is broken across lines, try to reconstruct it sensibly
            title_parts = [line['text'] for line in main_title_group]
            
            # Check if the first part ends with a colon
            if title_parts[0].endswith(':'):
                # Combine with the rest of the title
                if len(title_parts) > 1:
                    return title_parts[0] + ' ' + ' '.join(title_parts[1:])
            
            return full_title
                
        # Fallback methods if grouping doesn't work
        # Sort by font size (largest first) and position (top first)
        potential_titles = sorted(filtered_lines, key=lambda x: (-x['font_size'], x['top']))
        
        if potential_titles:
            # Check for title patterns in top lines
            for line in potential_titles[:5]:  # Check first few largest lines
                # If line contains a common title pattern
                if re.search(r'workshop:|webinar:|seminar:|presentation:', line['text'], re.IGNORECASE):
                    return line['text']
            
            # If no patterns found, return the largest text
            return potential_titles[0]['text']
            
        # Last resort: use any non-empty line
        if filtered_lines:
            return filtered_lines[0]['text']
            
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
