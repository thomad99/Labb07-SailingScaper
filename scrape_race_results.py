from bs4 import BeautifulSoup
import requests
import pandas as pd
from datetime import datetime
import time
import json
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from urllib.parse import urljoin, urlparse
import os
from database import Base, engine, SessionLocal

# Try to import from config, fall back to environment variables if config is missing
try:
    from config import DB_URL, SCRAPE_BASE_URL
except ImportError:
    DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sailing_results")
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    SCRAPE_BASE_URL = os.getenv("SCRAPE_BASE_URL", "https://example-sailing-results.com/results")

class Sailor(Base):
    __tablename__ = 'sailors'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    club = Column(String)
    age_category = Column(String)
    results = relationship("RaceResult", back_populates="sailor")

class Race(Base):
    __tablename__ = 'races'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    date = Column(DateTime)
    venue = Column(String)
    results = relationship("RaceResult", back_populates="race")

class RaceResult(Base):
    __tablename__ = 'race_results'
    id = Column(Integer, primary_key=True)
    sailor_id = Column(Integer, ForeignKey('sailors.id'))
    race_id = Column(Integer, ForeignKey('races.id'))
    position = Column(Integer)
    finish_time = Column(Float)  # Store as seconds for easy comparison
    boat_name = Column(String)
    
    sailor = relationship("Sailor", back_populates="results")
    race = relationship("Race", back_populates="results")

class SailingRaceScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls = set()
        self.session = SessionLocal()

    def get_page(self, url):
        """Fetch page content with error handling and rate limiting"""
        if url in self.visited_urls:
            return None
        
        try:
            # Add delay to be respectful to the server
            time.sleep(1)
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            self.visited_urls.add(url)
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_links(self, html, current_url):
        """Extract all relevant links from the page"""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            absolute_url = urljoin(current_url, href)
            
            # Only follow links from the same domain and results pages
            if (urlparse(absolute_url).netloc == self.domain and 
                'results' in absolute_url.lower() and
                absolute_url not in self.visited_urls):
                links.add(absolute_url)
        
        return links

    def parse_race_results(self, html, url):
        """Parse race results from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        try:
            # Example selectors - customize these based on the actual website structure
            race_containers = soup.find_all('div', class_='race-result')
            
            if not race_containers:
                print(f"No race results found on {url}")
                return []
            
            for race_elem in race_containers:
                try:
                    # Create Race entry
                    race = Race(
                        name=race_elem.find('h2', class_='race-name').text.strip(),
                        date=datetime.strptime(
                            race_elem.find('span', class_='date').text.strip(), 
                            '%Y-%m-%d'  # Adjust format based on website
                        ),
                        venue=race_elem.find('span', class_='venue').text.strip()
                    )
                    self.session.add(race)
                    self.session.flush()
                    
                    # Parse participant results
                    for participant in race_elem.find_all('div', class_='participant'):
                        try:
                            # Get or create sailor
                            sailor_name = participant.find('span', class_='skipper').text.strip()
                            sailor = self.session.query(Sailor).filter_by(name=sailor_name).first()
                            
                            if not sailor:
                                sailor = Sailor(
                                    name=sailor_name,
                                    club=participant.find('span', class_='club').text.strip(),
                                    age_category=participant.find('span', class_='category').text.strip()
                                )
                                self.session.add(sailor)
                                self.session.flush()
                            
                            # Create race result
                            result = RaceResult(
                                sailor_id=sailor.id,
                                race_id=race.id,
                                position=int(participant.find('span', class_='position').text.strip()),
                                finish_time=self.parse_time_to_seconds(
                                    participant.find('span', class_='time').text.strip()
                                ),
                                boat_name=participant.find('span', class_='boat-name').text.strip()
                            )
                            self.session.add(result)
                            
                        except Exception as e:
                            print(f"Error parsing participant in race {race.name}: {e}")
                            continue
                    
                    self.session.commit()
                    races.append(race)
                    
                except Exception as e:
                    print(f"Error parsing race on {url}: {e}")
                    self.session.rollback()
                    continue
                    
        except Exception as e:
            print(f"Error parsing page {url}: {e}")
            self.session.rollback()
        
        return races

    def parse_time_to_seconds(self, time_str):
        """Convert time string (HH:MM:SS) to seconds"""
        try:
            time_parts = time_str.split(':')
            if len(time_parts) == 3:
                hours, minutes, seconds = map(float, time_parts)
                return hours * 3600 + minutes * 60 + seconds
            return None
        except:
            return None

    def scrape_all_results(self):
        """Main function to scrape all race results recursively"""
        urls_to_visit = {self.base_url}
        
        while urls_to_visit:
            current_url = urls_to_visit.pop()
            print(f"Scraping: {current_url}")
            
            html = self.get_page(current_url)
            if html:
                # Parse results from current page
                self.parse_race_results(html, current_url)
                
                # Find new links to follow
                new_links = self.extract_links(html, current_url)
                urls_to_visit.update(new_links)
            
            print(f"Processed {len(self.visited_urls)} pages, {len(urls_to_visit)} remaining")

if __name__ == "__main__":
    scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    scraper.scrape_all_results() 
