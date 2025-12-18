import os
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv
import io

load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER", "uploads")

# Initialize Azure Blob Storage client
blob_service_client = None
container_client = None

if AZURE_STORAGE_CONNECTION_STRING:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
            print(f"Created Azure Blob container: {AZURE_STORAGE_CONTAINER_NAME}")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                print(f"Using existing Azure Blob container: {AZURE_STORAGE_CONTAINER_NAME}")
            else:
                print(f"Container creation error: {e}")
    except Exception as e:
        print(f"Failed to initialize Azure Blob Storage: {e}")
        print("Make sure AZURE_STORAGE_CONNECTION_STRING is set in .env file")
else:
    print("AZURE_STORAGE_CONNECTION_STRING not found in environment variables")
    print("Video upload and streaming features will not work")


@app.get("/")
async def read_root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video to Azure Blob Storage"""
    if not container_client:
        raise HTTPException(status_code=503, detail="Azure Blob Storage not configured")
    
    # Validate file type
    allowed_extensions = ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv']
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Upload to Azure Blob Storage
        blob_client = container_client.get_blob_client(file.filename)
        
        # Read file content
        content = await file.read()
        
        # Upload with content type
        content_type_map = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.ogg': 'video/ogg',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska'
        }
        
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings={
                'content_type': content_type_map.get(file_extension, 'video/mp4')
            }
        )
        
        return {
            "message": "Video uploaded successfully",
            "filename": file.filename,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/videos")
async def list_videos():
    """List available videos from Azure Blob Storage"""
    if not container_client:
        raise HTTPException(status_code=503, detail="Azure Blob Storage not configured")
    
    try:
        videos = []
        blob_list = container_client.list_blobs()
        
        for blob in blob_list:
            # Filter video files
            if Path(blob.name).suffix.lower() in ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv']:
                videos.append({
                    "name": blob.name,
                    "size": blob.size
                })
        
        return {"videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")


@app.get("/api/stream/{video_name}")
async def stream_video(video_name: str, request: Request):
    """Stream video from Azure Blob Storage with range support"""
    if not container_client:
        raise HTTPException(status_code=503, detail="Azure Blob Storage not configured")
    
    try:
        blob_client = container_client.get_blob_client(video_name)
        
        # Check if blob exists
        blob_properties = blob_client.get_blob_properties()
        file_size = blob_properties.size
        content_type = blob_properties.content_settings.content_type or "video/mp4"
        
        # Parse range header for seeking support
        range_header = request.headers.get("range")
        start = 0
        end = file_size - 1
        
        if range_header:
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else end
        
        content_length = end - start + 1
        
        # Download blob with range
        def iter_blob():
            stream = blob_client.download_blob(offset=start, length=content_length)
            for chunk in stream.chunks():
                yield chunk
        
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename={video_name}",
        }
        
        # If range request, return 206 Partial Content
        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(content_length)
            return StreamingResponse(
                iter_blob(),
                status_code=206,
                media_type=content_type,
                headers=headers
            )
        
        # Full file request
        return StreamingResponse(
            iter_blob(),
            media_type=content_type,
            headers=headers
        )
        
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming failed: {str(e)}")


@app.delete("/api/videos/{video_name}")
async def delete_video(video_name: str):
    """Delete video from Azure Blob Storage"""
    if not container_client:
        raise HTTPException(status_code=503, detail="Azure Blob Storage not configured")
    
    try:
        blob_client = container_client.get_blob_client(video_name)
        blob_client.delete_blob()
        
        return {"message": f"Video '{video_name}' deleted successfully"}
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
