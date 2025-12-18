from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the current directory
FRONTEND_DIR = Path(__file__).parent

@app.get("/")
async def read_root():
    """Serve the login page"""
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/index.html")
async def read_index():
    """Serve the login page"""
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/chat.html")
async def read_chat():
    """Serve the chat page"""
    return FileResponse(FRONTEND_DIR / "chat.html")

@app.get("/style.css")
async def read_style():
    """Serve the CSS file"""
    return FileResponse(FRONTEND_DIR / "style.css")

@app.get("/login.js")
async def read_login_js():
    """Serve the login JS file"""
    return FileResponse(FRONTEND_DIR / "login.js")

@app.get("/chat.js")
async def read_chat_js():
    """Serve the chat JS file"""
    return FileResponse(FRONTEND_DIR / "chat.js")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
