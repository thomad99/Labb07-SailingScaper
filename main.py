from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from chatbot import app as chatbot_app
from scrape_race_results import scrape_and_store
from database import Base, engine, SessionLocal
from models import Sailor, Race, RaceResult
from sqlalchemy import func
from typing import Optional
import requests

app = FastAPI()

# Create database tables
Base.metadata.create_all(engine)

# Mount the chatbot routes
app.mount("/api", chatbot_app)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Try to import from config, fall back to environment variables if config is missing
try:
    from config import SCRAPE_BASE_URL
except ImportError:
    SCRAPE_BASE_URL = os.getenv("SCRAPE_BASE_URL", "https://example-sailing-results.com/results")

@app.post("/trigger-scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Endpoint to trigger the scraping process"""
    background_tasks.add_task(scrape_and_store, SCRAPE_BASE_URL, lambda x: print(x))
    return {"message": "Scraping process started"}

@app.get("/scrape-status")
async def scrape_status():
    """Endpoint to check scraping status"""
    return {"status": "running"}  # Placeholder status tracking

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint - returns HTML page if browser requests it"""
    if request.headers.get("accept", "").startswith("text/html"):
        return templates.TemplateResponse("health.html", {"request": request})
    return {"status": "healthy"}

@app.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/db-status")
async def db_status():
    """Get database table counts"""
    with SessionLocal() as session:
        stats = {
            "sailors": session.query(func.count(Sailor.id)).scalar(),
            "races": session.query(func.count(Race.id)).scalar(),
            "race_results": session.query(func.count(RaceResult.id)).scalar(),
        }
    return stats

@app.get("/test-url")
async def test_url(url: str):
    """Test endpoint to verify URL fetch"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=10)
        return {
            "status": response.status_code,
            "content_length": len(response.text),
            "content_type": response.headers.get('content-type'),
            "preview": response.text[:1000]
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
