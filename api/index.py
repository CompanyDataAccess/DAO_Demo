from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
import fitz  # PyMuPDF
import io

app = FastAPI()

@app.post("/redact")
async def redact_pdf(file: UploadFile = File(...), search_strings: str = Form(...)):
    # 1. Read the incoming PDF into memory
    pdf_bytes = await file.read()
    doc = fitz.open("pdf", pdf_bytes)
    
    # 2. Get the strings Claude identified
    words_to_redact = search_strings.split(",")
    
    # 3. Search and draw black boxes
    for page in doc:
        for word in words_to_redact:
            if not word.strip():
                continue
            rectangles = page.search_for(word.strip())
            for rect in rectangles:
                page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()
        
    # 4. Save the redacted PDF to a memory buffer
    out_buffer = io.BytesIO()
    doc.save(out_buffer)
    
    # 5. Return the binary PDF file directly
    return Response(
        content=out_buffer.getvalue(), 
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="redacted.pdf"'}
    )
