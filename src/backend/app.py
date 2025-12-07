import os
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uuid

# Import the core modules from the same directory
from . import database as db
from . import storage
from . import processing
from . import llm_chain
from .worker import BackgroundProcessor, get_processor_instance # Import the worker logic

# --- 1. Initialization ---
app = FastAPI(title="Knowledge Atlas API")
app.docs_url = None
app.redoc_url = None

# Initialize CORS for frontend communication (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the database and start the processor thread
@app.on_event("startup")
def startup_event():
    db.init_db()
    
    # Get and start the single background processor instance
    processor = get_processor_instance()
    if not processor.is_alive():
        processor.start()
    print("Database and Background Processor started.")

# --- 2. API Endpoints ---

# Dependency to get the processor instance for queuing tasks
def get_processor() -> BackgroundProcessor:
    return get_processor_instance()

## A. Dashboard Data Endpoint (READ & SEARCH)
# Matches the requirements for pagination and keyword search
@app.get("/api/entries")
def get_entries(
    page: int = 1, 
    limit: int = 10, 
    keyword: Optional[str] = None
):
    """Fetches paginated and optionally filtered entries for the dashboard."""
    
    # 1. Fetch matching IDs using FTS5 if a keyword is provided
    if keyword:
        # Assumes database.py has a search_entries function using FTS5
        matching_ids = db.search_entries(keyword)
    else:
        matching_ids = None
    
    # 2. Fetch data, apply filtering, pagination, and total count
    # Assumes database.py has a get_paginated_entries function
    data_df, total_count = db.get_paginated_entries(
        page=page, 
        limit=limit, 
        matching_ids=matching_ids
    )

    # Convert DataFrame to list of dictionaries for JSON response
    return {
        "data": data_df.to_dict(orient="records"),
        "total": total_count
    }

## B. Upload Endpoint (CREATE)
# Handles the per-item submission from the UploadForm.tsx
@app.post("/api/upload")
async def upload_entry(
    processor: BackgroundProcessor = Depends(get_processor),
    # Common metadata fields passed as Form data
    theme: str = Form(...),
    entryDate: str = Form(...),
    # Type determines which field below is used
    type: str = Form(...), 
    
    # Optional fields (only one is present based on 'type')
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None) 
):
    # 1. Validate based on type
    if type == 'image' and file is None:
        raise HTTPException(status_code=400, detail="Image upload requires a file.")
    if type == 'link' and url is None:
        raise HTTPException(status_code=400, detail="Link upload requires a URL.")

    # 2. Upload/Stage the Source File
    source_url = None
    if type == 'image' and file:
        # Use a temporary path; the worker will handle final storage path
        file_extension = file.filename.split('.')[-1] if file.filename else 'dat'
        temp_path = f"temp/{uuid.uuid4()}.{file_extension}"
        
        # Read file contents into BytesIO to pass to storage module
        file_content = await file.read()
        file_stream = pd.io.common.BytesIO(file_content)

        # Assumes storage.upload_file can handle file streams
        source_url = storage.upload_file(file_stream, temp_path) 
        if not source_url:
            raise HTTPException(status_code=500, detail="Failed to upload file to storage.")
    
    elif type == 'link':
        source_url = url

    # 3. Create DB Entry and Queue Task
    entry_data = {
        "theme": theme,
        "source_type": type,
        "source_url": source_url,
        "entry_date": entryDate
    }
    
    new_id = db.add_entry(entry_data)
    
    # Add the task to the queue for background processing
    processor.add_task(new_id)

    return {"message": "Entry submitted and queued for processing.", "id": new_id}

## C. Reprocess Endpoint
@app.post("/api/reprocess/{entry_id}")
def reprocess_entry(entry_id: str, processor: BackgroundProcessor = Depends(get_processor)):
    """Sets entry status back to 'Uploaded' and re-queues the task."""
    
    entry = db.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")
        
    db.update_status(entry_id, "Uploaded")
    processor.add_task(entry_id)
    
    return {"message": f"Entry {entry_id} reset to Uploaded and re-queued."}

import gc
import asyncio
import logging
from typing import Dict, Any


process_semaphore = asyncio.Semaphore(int(os.getenv("SCHEDULER_CONCURRENT_LIMIT", 4)))
entries_active = set()
entries_lock = asyncio.Lock()

async def process_worker_wapper(worker_data: Dict[str, Any]):
    async with process_semaphore:
        try:
            await None #>> (**worker_data)
        except Exception as e:
            logging.exception(f"Processing worker error for {worker_data['entry_id']}: {e}")
        finally:
            async with entries_lock:
                await asyncio.sleep(5)  # Make sure frontend has time to fetch final status
                entries_lock.discard(worker_data['entry_id'])

@app.post("/schedule_processing_jobs")
async def schedule_processing_jobs(
    credentials: str,
    entry_ids: List[str],
):  
    # verify credentials
    new_entry_ids = [x for x in entry_ids if (x not in entries_active)]
    try:
        for entry_id in entry_ids:
            asyncio.create_task(
                process_worker_wapper({
                    'entry_id': entry_id
                })
            )
            # Update metadata to queued

    except Exception as e:
        pass
    finally:
        gc.collect()