import streamlit as st
import os
import zipfile
import tempfile
import time
from io import BytesIO

from pdf_processor import extract_pdfs_from_zip, is_pdf_file
from ocr_utils import extract_title_from_pdf
from ppt_generator import convert_pdf_to_ppt

st.set_page_config(
    page_title="PDF to PowerPoint Converter",
    page_icon="📄",
    layout="wide"
)

st.title("PDF to PowerPoint Converter")
st.write("""
Upload PDF files or a ZIP archive containing PDFs, and we'll convert them to PowerPoint presentations.
The title of each PDF will be automatically extracted using OCR to name the PowerPoint file.
""")

# File uploader that accepts PDFs and ZIP files
uploaded_files = st.file_uploader(
    "Upload PDF file(s) or ZIP archives containing PDFs",
    type=["pdf", "zip"],
    accept_multiple_files=True
)

if uploaded_files:
    pdf_files = []
    
    # Process the uploaded files (extract PDFs from ZIPs if necessary)
    with st.spinner("Processing uploaded files..."):
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith('.zip'):
                # Extract PDFs from ZIP
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = os.path.join(temp_dir, "archive.zip")
                    with open(zip_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    
                    extracted_pdfs = extract_pdfs_from_zip(zip_path, temp_dir)
                    if extracted_pdfs:
                        pdf_files.extend(extracted_pdfs)
                    else:
                        st.warning(f"No PDF files found in ZIP archive: {uploaded_file.name}")
            elif is_pdf_file(uploaded_file):
                # Add PDF directly
                pdf_files.append({"name": uploaded_file.name, "content": uploaded_file.getvalue()})
            else:
                st.warning(f"Unsupported file type: {uploaded_file.name}")

    if pdf_files:
        st.write(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF and convert to PPT
        converted_files = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, pdf_file in enumerate(pdf_files):
            try:
                status_text.text(f"Processing {pdf_file['name']} ({i+1}/{len(pdf_files)})")
                
                # Extract title using OCR
                title = extract_title_from_pdf(BytesIO(pdf_file['content']))
                if not title:
                    title = os.path.splitext(pdf_file['name'])[0]  # Use filename as fallback
                
                # Convert PDF to PPT
                ppt_bytes = convert_pdf_to_ppt(BytesIO(pdf_file['content']), title)
                
                # Add to converted files
                ppt_filename = f"{title}.pptx"
                converted_files.append({"name": ppt_filename, "content": ppt_bytes})
                
                progress_bar.progress((i + 1) / len(pdf_files))
            except Exception as e:
                st.error(f"Error processing {pdf_file['name']}: {str(e)}")
        
        status_text.text("Processing complete!")
        time.sleep(1)  # Give users a moment to see the complete status
        status_text.empty()
        progress_bar.empty()
        
        if converted_files:
            st.success(f"Successfully converted {len(converted_files)} files")
            
            # Display download buttons for each converted file
            st.subheader("Download Converted Presentations")
            
            for ppt_file in converted_files:
                st.download_button(
                    label=f"Download {ppt_file['name']}",
                    data=ppt_file['content'],
                    file_name=ppt_file['name'],
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
            
            # Also provide a ZIP with all presentations
            if len(converted_files) > 1:
                with BytesIO() as zip_buffer:
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for ppt_file in converted_files:
                            zip_file.writestr(ppt_file['name'], ppt_file['content'])
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label="Download All Presentations (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="all_presentations.zip",
                        mime="application/zip"
                    )
        else:
            st.warning("No presentations were successfully converted")
    else:
        st.warning("No valid PDF files found to process")

# Add some instructions at the bottom
st.markdown("---")
st.subheader("Instructions")
st.markdown("""
1. Upload one or more PDF files, or ZIP archives containing PDFs
2. Wait for the processing to complete
3. Download the converted PowerPoint files individually or as a ZIP archive
4. For best results, ensure the PDF has clear text on the first page for title extraction
""")
