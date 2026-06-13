from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
import fitz  # PyMuPDF
import io
import json

app = FastAPI()

@app.post("/redact")
async def redact_pdf(
    file: UploadFile = File(...), 
    search_strings: str = Form(""), 
    boxes_json: str = Form("[]")
):
    # 1. Read the incoming PDF into memory
    pdf_bytes = await file.read()
    doc = fitz.open("pdf", pdf_bytes)
    
    # 2. Try Exact Text Redaction (Perfect Accuracy for normal PDFs)
    text_found = False
    if search_strings:
        # Split by comma and clean up whitespace
        strings = [s.strip() for s in search_strings.split(",") if s.strip()]
        for page in doc:
            for text in strings:
                # search_for gives pixel-perfect coordinates automatically
                text_instances = page.search_for(text)
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=(0, 0, 0))
                    text_found = True
    
    # 3. If no text was found (meaning it's a scanned image), fallback to Bounding Boxes
    if not text_found:
        try:
            boxes = json.loads(boxes_json)
        except:
            boxes = []
            
        for item in boxes:
            page_index = item.get("page", 1) - 1
            if page_index < 0 or page_index >= len(doc):
                continue
                
            page = doc[page_index]
            width, height = page.rect.width, page.rect.height
            
            b = item.get("box", [0, 0, 0, 0])
            if len(b) == 4:
                ymin, xmin, ymax, xmax = b[0], b[1], b[2], b[3]
                
                x0 = (xmin / 1000.0) * width
                y0 = (ymin / 1000.0) * height
                x1 = (xmax / 1000.0) * width
                y1 = (ymax / 1000.0) * height
                
                pad_x = (x1 - x0) * 0.15
                pad_y = (y1 - y0) * 0.15
                
                rect = fitz.Rect(max(0, x0-pad_x), max(0, y0-pad_y), min(width, x1+pad_x), min(height, y1+pad_y))
                page.add_redact_annot(rect, fill=(0, 0, 0))
    
    # 4. Apply all redactions
    for page in doc:
        page.apply_redactions()
        
    out_buffer = io.BytesIO()
    doc.save(out_buffer)
    
    original_name = file.filename if file.filename else "redacted.pdf"
    
    return Response(
        content=out_buffer.getvalue(), 
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{original_name}"'}
    )
