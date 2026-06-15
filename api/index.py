from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
import fitz  # PyMuPDF
import io

app = FastAPI()

@app.post("/redact")
async def redact_pdf(
    file: UploadFile = File(...), 
    search_strings: str = Form("")
):
    # 1. Read the incoming PDF into memory
    pdf_bytes = await file.read()
    doc = fitz.open("pdf", pdf_bytes)
    
    # 2. Exact Text Redaction
    if search_strings:
        # Split by comma and clean up whitespace
        strings = [s.strip() for s in search_strings.split(",") if s.strip()]
        for page in doc:
            for text in strings:
                # search_for gives pixel-perfect coordinates automatically
                text_instances = page.search_for(text)
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
    
    # 3. Apply all redactions
    for page in doc:
        page.apply_redactions()
        
    out_buffer = io.BytesIO()
    doc.save(out_buffer)
    
    original_name = f"Redacted_{file.filename}" if file.filename else "Redacted_document.pdf"
    
    return Response(
        content=out_buffer.getvalue(), 
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{original_name}"'}
    )
