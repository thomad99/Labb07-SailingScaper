from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
import os
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import threading

DATABASE_URL = os.getenv("DATABASE_URL")
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class RegattaResult(Base):
    __tablename__ = "regatta_results"
    id = Column(Integer, primary_key=True, index=True)
    regatta_name = Column(String, index=True)
    regatta_date = Column(String, index=True)
    race_category = Column(String, index=True)
    pos = Column(Integer)
    sail = Column(String)
    boat = Column(String)
    skipper = Column(String)
    yacht_club = Column(String)
    results = Column(Text)
    total_points = Column(Integer)

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
progress_log = []

def add_progress_message(message):
    progress_log.append(message)

def scrape_and_store(url, progress_callback):
    try:
        progress_callback(f"Starting scrape for {url}")
        response = requests.get(url)
        if response.status_code != 200:
            progress_callback(f"Failed to retrieve page: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        regatta_name = soup.find("h2").text.strip() if soup.find("h2") else "Unknown Regatta"
        regatta_date = soup.find("h3").text.strip() if soup.find("h3") else "Unknown Date"
        
        tables = soup.find_all("table")
        progress_callback(f"Total tables found: {len(tables)}")
        
        session = SessionLocal()
        total_results = 0
        
        for table in tables:
            headers = [th.text.strip() for th in table.find_all("th")]
            if "Pos" in headers and "Sail" in headers:
                race_category = table.find_previous("h4").text.strip() if table.find_previous("h4") else "Unknown Category"
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 7:
                        result = RegattaResult(
                            regatta_name=regatta_name,
                            regatta_date=regatta_date,
                            race_category=race_category,
                            pos=int(cols[0].text.strip()),
                            sail=cols[1].text.strip(),
                            boat=cols[2].text.strip(),
                            skipper=cols[3].text.strip(),
                            yacht_club=cols[4].text.strip(),
                            results=cols[5].text.strip(),
                            total_points=int(cols[6].text.strip())
                        )
                        session.add(result)
                        total_results += 1
        session.commit()
        session.close()
        progress_callback(f"Scraping complete: {total_results} results extracted.")
    except Exception as e:
        progress_callback(f"Error: {str(e)}")

@app.post("/trigger-scrape")
async def trigger_scrape(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    url = data.get("url")
    if not url:
        return {"error": "URL is required"}
    
    background_tasks.add_task(scrape_and_store, url, add_progress_message)
    return {"message": f"Scraping started for {url}"}

@app.get("/get-progress")
async def get_progress():
    return {"progress": progress_log}

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
