from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from chatbot import app as chatbot_app
from scrape_race_results import SailingRaceScraper
from database import Base, engine, SessionLocal
from sqlalchemy import func

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

def run_scraper():
    scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    scraper.scrape_all_results()

@app.post("/trigger-scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Endpoint to trigger the scraping process"""
    scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    summary = scraper.scrape_all_results()
    return {
        "message": "Scraping process completed",
        "summary": summary
    }

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
async def health_check():
    return {"status": "healthy"}

@app.get("/admin")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/db-status")
async def db_status():
    """Get database table counts"""
    from scrape_race_results import Sailor, Race, RaceResult
    
    with SessionLocal() as session:
        stats = {
            "sailors": session.query(func.count(Sailor.id)).scalar(),
            "races": session.query(func.count(Race.id)).scalar(),
            "race_results": session.query(func.count(RaceResult.id)).scalar(),
        }
    return stats

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 
