import os
import zipfile
from io import BytesIO
import tempfile

def is_pdf_file(file_obj):
    """Check if a file is a PDF based on its name and content."""
    if not file_obj.name.lower().endswith('.pdf'):
        return False
    
    # Check for PDF magic number (%PDF-)
    file_content = file_obj.read(4)
    file_obj.seek(0)  # Reset pointer to beginning of file
    return file_content == b'%PDF'

def extract_pdfs_from_zip(zip_path, extract_dir):
    """
    Extract PDF files from a ZIP archive.
    
    Args:
        zip_path: Path to the ZIP file
        extract_dir: Directory to extract files to
        
    Returns:
        List of dictionaries with name and content of extracted PDFs
    """
    pdf_files = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of all files in the archive
            file_list = zip_ref.namelist()
            
            # Extract only PDF files
            for file_name in file_list:
                if file_name.lower().endswith('.pdf'):
                    # Extract the file
                    pdf_path = os.path.join(extract_dir, os.path.basename(file_name))
                    with zip_ref.open(file_name) as source, open(pdf_path, 'wb') as target:
                        target.write(source.read())
                    
                    # Read the PDF content
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_content = pdf_file.read()
                    
                    pdf_files.append({
                        "name": os.path.basename(file_name),
                        "content": pdf_content
                    })
    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file provided")
    
    return pdf_files

def count_pages_in_pdf(pdf_data):
    """
    Count the number of pages in a PDF file.
    
    Args:
        pdf_data: PDF file content as BytesIO object
        
    Returns:
        Number of pages in the PDF
    """
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(pdf_data)
        return len(pdf_reader.pages)
    except Exception as e:
        raise ValueError(f"Error counting pages in PDF: {str(e)}")
