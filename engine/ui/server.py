import uuid
import os
import sys
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Ensure engine is in python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.draft_generator import generate_draft
from engine.ui.database import create_job, get_job, get_all_jobs, init_db, delete_job, reset_job_status
from engine.ui.tracker import SQLiteTracker

import dotenv
dotenv.load_dotenv(Path(__file__).parent.parent.parent / '.env')

app = FastAPI(title="OpenDraft UI API")

@app.on_event("startup")
def startup_event():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DraftRequest(BaseModel):
    topic: str
    level: str = "research_paper"
    language: str = "pt"
    citation_style: str = "abnt"
    author: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    message: str

def background_draft_task(job_id: str, request: DraftRequest):
    tracker = SQLiteTracker(job_id)
    output_dir = Path(__file__).parent.parent.parent / "outputs" / job_id
    
    try:
        pdf_path, docx_path = generate_draft(
            topic=request.topic,
            language=request.language,
            academic_level=request.level,
            citation_style=request.citation_style,
            author_name=request.author,
            tracker=tracker,
            output_dir=output_dir,
            skip_validation=False,
            verbose=False,
        )
        
        # Update db with paths
        from engine.ui.database import get_db
        conn = get_db()
        conn.execute("UPDATE jobs SET pdf_path = ?, docx_path = ? WHERE id = ?", (str(pdf_path), str(docx_path), job_id))
        conn.commit()
        conn.close()
        
    except Exception as e:
        # Error is already caught and logged by draft_generator, tracker is marked failed.
        print(f"Background task failed for job {job_id}: {e}")


@app.post("/api/jobs", response_model=JobResponse)
def create_draft_job(request: DraftRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    create_job(job_id, request.topic, request.level)
    
    background_tasks.add_task(background_draft_task, job_id, request)
    return {"job_id": job_id, "message": "Draft generation started"}


def background_draft_task_resume(job_id: str, topic: str, level: str, checkpoint_path: Path, output_dir: Path):
    tracker = SQLiteTracker(job_id)
    try:
        pdf_path, docx_path = generate_draft(
            topic=topic,
            language="pt",
            academic_level=level,
            citation_style="abnt",
            tracker=tracker,
            output_dir=output_dir,
            resume_from=checkpoint_path,
            skip_validation=False,
            verbose=False,
        )
        
        from engine.ui.database import get_db
        conn = get_db()
        conn.execute("UPDATE jobs SET pdf_path = ?, docx_path = ? WHERE id = ?", (str(pdf_path), str(docx_path), job_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Resume task failed for job {job_id}: {e}")

@app.post("/api/jobs/{job_id}/resume")
def resume_job_endpoint(job_id: str, background_tasks: BackgroundTasks):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    output_dir = Path(__file__).parent.parent.parent / "outputs" / job_id
    checkpoint_path = output_dir / "checkpoint.json"
    
    if not checkpoint_path.exists():
        raise HTTPException(status_code=400, detail="No checkpoint found to resume from")
        
    reset_job_status(job_id)
    background_tasks.add_task(background_draft_task_resume, job_id, job['topic'], job['level'], checkpoint_path, output_dir)
    return {"message": "Job resumed successfully"}



@app.get("/api/jobs")
def list_jobs():
    return get_all_jobs()


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # parse progress details if possible
    import json
    if job.get('progress_details'):
        try:
            job['progress_details'] = json.loads(job['progress_details'])
        except json.JSONDecodeError:
            pass
            
    return job

@app.get("/api/jobs/{job_id}/draft")
def get_job_draft(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if not job.get('pdf_path'):
        raise HTTPException(status_code=404, detail="Draft not ready yet")
        
    md_path = str(job['pdf_path']).replace('.pdf', '.md')
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="Markdown draft file not found")
        
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    return {"content": content}

@app.delete("/api/jobs/{job_id}")
def delete_job_endpoint(job_id: str):
    import shutil
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    output_dir = Path(__file__).parent.parent.parent / "outputs" / job_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
        
    # fallback to delete if it was generated in the old 'generated_draft' folder
    if job.get('pdf_path') and 'generated_draft' in str(job['pdf_path']):
        try:
            pdf_path = Path(str(job['pdf_path']))
            if pdf_path.exists(): pdf_path.unlink()
            docx_path = Path(str(job['docx_path']))
            if docx_path.exists(): docx_path.unlink()
            md_path = Path(str(job['pdf_path']).replace('.pdf', '.md'))
            if md_path.exists(): md_path.unlink()
        except:
            pass
            
    delete_job(job_id)
    return {"message": "Job deleted successfully"}

# Entry point for running the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
