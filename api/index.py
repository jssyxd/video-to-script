import os
import sys

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now we can import from app/ which is at project root level
from fastapi import FastAPI
from fastapi.responses import FileResponse

# Initialize database and routes
from app.database import init_db
from app.routes import jobs

init_db()

app = FastAPI()
app.include_router(jobs.router)

# Serve static files
static_dir = os.path.join(project_root, "static")

@app.get("/")
async def root():
    # Try static/index.html first, then api/home.html as fallback
    static_index = os.path.join(static_dir, "index.html")
    api_home = os.path.join(os.path.dirname(__file__), "home.html")

    if os.path.exists(static_index):
        return FileResponse(static_index)
    elif os.path.exists(api_home):
        return FileResponse(api_home)
    return {"message": "Video to Script API"}

@app.get("/static/{path:path}")
async def static_files(path: str):
    file_path = os.path.join(static_dir, path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "Not found"}, 404