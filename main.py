from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from chatbot import app as chatbot_app
from scrape_race_results import SailingRaceScraper
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

# Add at the top level of the file
active_scraper: Optional[SailingRaceScraper] = None

def run_scraper():
    scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    scraper.scrape_all_results()

@app.post("/trigger-scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Endpoint to trigger the scraping process"""
    global active_scraper
    
    if active_scraper:
        return {"message": "Scraper is already running"}
    
    active_scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    try:
        summary = active_scraper.scrape_all_results()
        return {
            "message": "Scraping process completed",
            "summary": summary
        }
    finally:
        active_scraper = None

@app.post("/stop-scrape")
async def stop_scrape():
    """Endpoint to stop the scraping process"""
    global active_scraper
    
    if active_scraper:
        active_scraper.stop_scraping()
        return {"message": "Stopping scraper..."}
    return {"message": "No active scraper to stop"}

@app.get("/scrape-status")
async def scrape_status():
    """Endpoint to check scraping status"""
    # You might want to add a status tracking mechanism
    return {"status": "running"}  # or "completed" or "failed"

# Serve static files if you have any
# app.mount("/static", StaticFiles(directory="static"), name="static")

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

@app.post("/scrape")
async def scrape_url(request: dict):
    try:
        url = request.get("url")
        scraper = SailingRaceScraper(url)
        result = scraper.scrape_all_results()
        
        # Ensure we have all required fields
        response = {
            "url_processed": url,
            "total_races": result.get("total_races", 0),
            "total_results": result.get("total_results", 0),
            "categories": result.get("categories", []),
            "elapsed_time": result.get("elapsed_time", "unknown"),
            "stop_reason": result.get("stop_reason", "completed"),
            "debug_info": {
                "html_length": len(scraper.last_html) if hasattr(scraper, "last_html") else 0,
                "tables_found": scraper.tables_found if hasattr(scraper, "tables_found") else 0,
                "parse_errors": scraper.parse_errors if hasattr(scraper, "parse_errors") else []
            }
        }
        
        return response
        
    except Exception as e:
        print(f"Error in scrape endpoint: {str(e)}")
        return {
            "error": str(e),
            "url_processed": url,
            "total_races": 0,
            "total_results": 0,
            "categories": [],
            "elapsed_time": "error",
            "stop_reason": f"error: {str(e)}"
        }

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
