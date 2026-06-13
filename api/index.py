from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
import fitz  # PyMuPDF
import io
import json

app = FastAPI()

@app.post("/redact")
async def redact_pdf(file: UploadFile = File(...), boxes_json: str = Form(...)):
    # 1. Read the incoming PDF into memory
    pdf_bytes = await file.read()
    doc = fitz.open("pdf", pdf_bytes)
    
    # 2. Parse the JSON boxes from Gemini
    # Expected format: [{"page": 1, "box": [ymin, xmin, ymax, xmax]}]
    try:
        boxes = json.loads(boxes_json)
    except:
        boxes = []
        
    # 3. Draw black boxes blindly over coordinates
    for item in boxes:
        # Get page (Gemini usually uses 1-indexed pages, PyMuPDF uses 0-indexed)
        page_index = item.get("page", 1) - 1
        if page_index < 0 or page_index >= len(doc):
            continue
            
        page = doc[page_index]
        page_rect = page.rect
        width = page_rect.width
        height = page_rect.height
        
        # Gemini bounding boxes are [ymin, xmin, ymax, xmax] scaled 0 to 1000
        b = item.get("box", [0, 0, 0, 0])
        if len(b) == 4:
            ymin, xmin, ymax, xmax = b[0], b[1], b[2], b[3]
            
            # Convert 1000-scale coordinates to actual PDF pixels/points
            x0 = (xmin / 1000.0) * width
            y0 = (ymin / 1000.0) * height
            x1 = (xmax / 1000.0) * width
            y1 = (ymax / 1000.0) * height
            
            # Create a rectangle and draw it
            rect = fitz.Rect(x0, y0, x1, y1)
            page.add_redact_annot(rect, fill=(0, 0, 0))
    
    # Apply all redactions across all pages
    for page in doc:
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
