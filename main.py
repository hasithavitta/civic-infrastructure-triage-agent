import os
import uvicorn
import secrets
from fastapi import FastAPI, HTTPException, Form, UploadFile, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from dataclasses import asdict

# Import orchestrator logic
from orchestrator import process_report

app = FastAPI(
    title="Civic Triage Agent API",
    description="FastAPI wrapper for citizen infrastructure reports triage",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    triage_key = os.environ.get("TRIAGE_API_KEY")
    demo_key = os.environ.get("TRIAGE_DEMO_API_KEY")
    if not triage_key and not demo_key:
        raise HTTPException(
            status_code=500,
            detail="TRIAGE_API_KEY environment variable is not configured on the server."
        )
    
    match_triage = triage_key and x_api_key and secrets.compare_digest(x_api_key, triage_key)
    match_demo = demo_key and x_api_key and secrets.compare_digest(x_api_key, demo_key)
    
    if not (match_triage or match_demo):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

def verify_admin_api_key(x_api_key: Optional[str] = Header(None)):
    triage_key = os.environ.get("TRIAGE_API_KEY")
    if not triage_key:
        raise HTTPException(
            status_code=500,
            detail="TRIAGE_API_KEY environment variable is not configured on the server."
        )
    
    if not x_api_key or not secrets.compare_digest(x_api_key, triage_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing Admin API key"
        )

@app.get("/")
def health_check():
    """Simple health check endpoint for Cloud Run health checks."""
    return {"status": "ok", "version": "client-side-reveal-v1"}

@app.post("/triage", dependencies=[Depends(verify_api_key)])
def triage_report(
    raw_text: Optional[str] = Form(None),
    image: Optional[UploadFile] = None
):
    """Triage endpoint that runs the orchestrator pipeline accepting multipart/form-data."""
    text_present = raw_text is not None and bool(raw_text.strip())
    image_present = image is not None and bool(image.filename)
    
    if not text_present and not image_present:
        raise HTTPException(
            status_code=400, 
            detail="At least one of 'raw_text' or 'image' must be provided."
        )
    
    image_bytes = None
    image_mime_type = None
    image_filename = None
    
    if image_present:
        # Validate that the file is an actual image
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded file must be a valid image. Got: {image.content_type}"
            )
        
        try:
            image_bytes = image.file.read()
            image_mime_type = image.content_type
            image_filename = image.filename
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read uploaded image file: {str(e)}"
            )

    try:
        report = process_report(
            raw_text=raw_text if text_present else None,
            image_filename=image_filename,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type
        )
        return asdict(report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/reports/{report_id}/resolve", dependencies=[Depends(verify_admin_api_key)])
def resolve_report(report_id: str):
    """Marks a report as resolved in Supabase."""
    from agents.storage import db
    try:
        response = db.table("reports").select("report_id").eq("report_id", report_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Report not found")
        
        db.table("reports").update({"status": "resolved"}).eq("report_id", report_id).execute()
        return {"status": "success", "message": f"Report {report_id} marked as resolved."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Get port from environment, defaulting to 8080 (standard for Cloud Run)
    port = int(os.environ.get("PORT", 8080))
    # Run uvicorn on 0.0.0.0
    uvicorn.run("main:app", host="0.0.0.0", port=port)
