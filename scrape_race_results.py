from bs4 import BeautifulSoup
import requests
import pandas as pd
from datetime import datetime
import time
import json
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from urllib.parse import urljoin, urlparse
import os
from database import Base, engine, SessionLocal
import re

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

class RaceCategory(Base):
    __tablename__ = 'race_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String)  # e.g., "Sunfish", "M15", "E Scow", etc.
    races = relationship("Race", back_populates="category")

class Race(Base):
    __tablename__ = 'races'
    id = Column(Integer, primary_key=True)
    name = Column(String)  # e.g., "Summer Series Race 1"
    date = Column(DateTime)
    venue = Column(String)
    category_id = Column(Integer, ForeignKey('race_categories.id'))
    event_name = Column(String)  # e.g., "Summer Series 2023"
    weather_conditions = Column(String, nullable=True)
    
    category = relationship("RaceCategory", back_populates="races")
    results = relationship("RaceResult", back_populates="race")

class RaceResult(Base):
    __tablename__ = 'race_results'
    id = Column(Integer, primary_key=True)
    sailor_id = Column(Integer, ForeignKey('sailors.id'))
    race_id = Column(Integer, ForeignKey('races.id'))
    position = Column(Integer)
    sail_number = Column(String)  # Added for sail number
    boat_name = Column(String)
    yacht_club = Column(String)  # Moved from Sailor to RaceResult as it might change
    points = Column(Float)  # Added for race points
    total_points = Column(Float)  # Added for total series points
    finish_time = Column(Float, nullable=True)
    dnf = Column(Boolean, default=False)
    dns = Column(Boolean, default=False)
    
    sailor = relationship("Sailor", back_populates="results")
    race = relationship("Race", back_populates="results")

class SailingRaceScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls = set()
        self.session = SessionLocal()
        self.should_stop = False
        self.max_pages = 100  # Maximum pages to scrape
        self.timeout = 3600  # Maximum runtime in seconds (1 hour)
        self.start_time = None

    def stop_scraping(self):
        """Signal the scraper to stop"""
        self.should_stop = True

    def check_should_stop(self):
        """Check if scraping should stop"""
        if self.should_stop:
            return True
        
        if len(self.visited_urls) >= self.max_pages:
            print(f"Reached maximum page limit of {self.max_pages}")
            return True
        
        if self.start_time and (time.time() - self.start_time) > self.timeout:
            print(f"Reached timeout limit of {self.timeout} seconds")
            return True
        
        return False

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
        """Parse race results from Regatta Network"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        try:
            print("\n=== Page Content Analysis ===")
            print(f"URL being processed: {url}")
            
            # Print HTML for debugging
            print("\nFirst 1000 characters of HTML:")
            print(html[:1000])
            
            # Find the main content
            content = soup.find('div', {'id': 'contentTable'}) or soup
            
            # Find all tables - Regatta Network uses tables for results
            tables = content.find_all('table')
            print(f"\nFound {len(tables)} tables")
            
            # Process each table as a separate race category
            for table in tables:
                try:
                    # Try to find the category name from preceding text
                    header = table.find_previous(['h2', 'h3', 'strong', 'b'])
                    category_name = header.text.strip() if header else "Unknown Category"
                    print(f"\nProcessing table with category: {category_name}")
                    
                    # Create category
                    category = self.session.query(RaceCategory).filter_by(name=category_name).first()
                    if not category:
                        category = RaceCategory(name=category_name)
                        self.session.add(category)
                        self.session.flush()
                    
                    # Create race
                    race = Race(
                        name=f"Cherry Pie Regatta - {category_name}",
                        date=datetime(2025, 2, 15),  # Hardcoded from event name
                        venue="Sarasota Sailing Squadron",
                        category_id=category.id,
                        event_name="Cherry Pie Regatta"
                    )
                    self.session.add(race)
                    self.session.flush()
                    
                    # Process results
                    rows = table.find_all('tr')
                    print(f"Found {len(rows)} rows in table")
                    
                    # Skip first row (headers)
                    for row in rows[1:]:
                        try:
                            cells = row.find_all('td')
                            if len(cells) < 5:  # Need at least position, sail, name, club
                                continue
                            
                            # Extract data
                            pos_text = cells[0].text.strip()
                            if not pos_text or not any(c.isdigit() for c in pos_text):
                                continue
                                
                            position = int(''.join(c for c in pos_text if c.isdigit()))
                            sail_number = cells[1].text.strip()
                            skipper_name = cells[3].text.strip()  # Adjust index based on actual data
                            yacht_club = cells[4].text.strip()
                            
                            print(f"Processing result: Pos={position}, Sail={sail_number}, Skipper={skipper_name}")
                            
                            # Create or get sailor
                            sailor = self.session.query(Sailor).filter_by(name=skipper_name).first()
                            if not sailor:
                                sailor = Sailor(name=skipper_name, club=yacht_club)
                                self.session.add(sailor)
                                self.session.flush()
                            
                            # Create result
                            result = RaceResult(
                                sailor_id=sailor.id,
                                race_id=race.id,
                                position=position,
                                sail_number=sail_number,
                                yacht_club=yacht_club
                            )
                            self.session.add(result)
                            print(f"Added result for {skipper_name}")
                            
                        except Exception as e:
                            print(f"Error processing row: {e}")
                            continue
                    
                    self.session.commit()
                    races.append(race)
                    
                except Exception as e:
                    print(f"Error processing table: {e}")
                    self.session.rollback()
                    continue
                
        except Exception as e:
            print(f"Error parsing page: {e}")
            self.session.rollback()
        
        return races

    def parse_date(self, date_string):
        """Try multiple date formats"""
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%B %d %Y',
            '%b %d %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        return datetime.now()

    def scrape_all_results(self):
        """Main function to scrape single URL"""
        self.start_time = time.time()
        self.should_stop = False
        total_races = 0
        total_results = 0
        categories_found = set()
        
        print(f"Scraping URL: {self.base_url}")
        
        # Only scrape the single provided URL
        html = self.get_page(self.base_url)
        if html:
            # Parse results from page
            races = self.parse_race_results(html, self.base_url)
            total_races += len(races)
            
            # Count results and categories
            for race in races:
                categories_found.add(race.category.name)
                total_results += len(race.results)
        
        # Include stop reason in summary
        elapsed_time = time.time() - self.start_time
        stop_reason = "Completed single page scrape"
        
        # Print final summary
        print("\n=== Scraping Summary ===")
        print(f"URL processed: {self.base_url}")
        print(f"Total races found: {total_races}")
        print(f"Total race results: {total_results}")
        print(f"Race categories found: {len(categories_found)}")
        print("\nCategories:")
        for category in sorted(categories_found):
            category_results = self.session.query(RaceResult)\
                .join(Race)\
                .join(RaceCategory)\
                .filter(RaceCategory.name == category)\
                .count()
            print(f"- {category}: {category_results} results")
        
        return {
            'url_processed': self.base_url,
            'total_races': total_races,
            'total_results': total_results,
            'categories': list(categories_found),
            'elapsed_time': f"{elapsed_time:.1f} seconds",
            'stop_reason': stop_reason
        }

if __name__ == "__main__":
    scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    scraper.scrape_all_results() 
