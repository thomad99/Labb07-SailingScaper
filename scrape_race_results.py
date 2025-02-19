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
        """Parse race results from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        try:
            print("\n=== Page Content Analysis ===")
            print(f"URL being processed: {url}")
            
            # Print the first part of HTML to see what we're working with
            print("\nFirst 500 characters of HTML:")
            print(html[:500])
            
            # Try to find race data with different possible selectors
            race_sections = []
            possible_selectors = [
                'div.race-category',  # Original selector
                'div.race',           # Alternative
                'table.results',      # Direct table
                'table',              # Any table
            ]
            
            for selector in possible_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"\nFound {len(elements)} elements with selector: {selector}")
                    race_sections = elements
                    break
            
            if not race_sections:
                print("\nNo race sections found. Available classes in HTML:")
                for tag in soup.find_all(class_=True):
                    print(f"Tag: {tag.name}, Classes: {tag['class']}")
            
            for section in race_sections:
                try:
                    # Try to find race category
                    category_name = None
                    for selector in ['h2.category-name', 'h2', 'th', 'caption']:
                        element = section.select_one(selector)
                        if element:
                            category_name = element.text.strip()
                            print(f"\nFound category: {category_name}")
                            break
                    
                    if not category_name:
                        category_name = "Uncategorized"
                        print("\nNo category found, using 'Uncategorized'")
                    
                    # Get or create race category
                    category = self.session.query(RaceCategory).filter_by(name=category_name).first()
                    if not category:
                        category = RaceCategory(name=category_name)
                        self.session.add(category)
                        self.session.flush()
                    
                    # Try to find date
                    date_text = None
                    date_patterns = [
                        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                        r'\d{2}/\d{2}/\d{4}',   # MM/DD/YYYY
                        r'\w+ \d{1,2},? \d{4}'  # Month DD, YYYY
                    ]
                    
                    for pattern in date_patterns:
                        matches = re.findall(pattern, str(section))
                        if matches:
                            date_text = matches[0]
                            print(f"Found date: {date_text}")
                            break
                    
                    race_date = datetime.now() if not date_text else self.parse_date(date_text)
                    
                    # Create race
                    race = Race(
                        name=f"Race - {category_name} - {race_date.strftime('%Y-%m-%d')}",
                        date=race_date,
                        venue="Unknown",  # We can enhance this later
                        category_id=category.id,
                        event_name=category_name
                    )
                    self.session.add(race)
                    self.session.flush()
                    
                    # Find results - look for table or structured data
                    results_data = []
                    if section.name == 'table':
                        results_table = section
                    else:
                        results_table = section.find('table')
                    
                    if results_table:
                        print("\nFound results table")
                        # Get headers
                        headers = []
                        for th in results_table.find_all(['th', 'td']):
                            headers.append(th.text.strip().lower())
                            if len(headers) > 0:  # Found header row
                                break
                        
                        print(f"Table headers found: {headers}")
                        
                        # Process rows
                        for row in results_table.find_all('tr'):
                            cells = row.find_all('td')
                            if len(cells) >= len(headers):  # Skip header row
                                row_data = {}
                                for i, cell in enumerate(cells):
                                    if i < len(headers):
                                        row_data[headers[i]] = cell.text.strip()
                                results_data.append(row_data)
                        
                        print(f"Found {len(results_data)} result rows")
                    
                    # Process results
                    for data in results_data:
                        try:
                            # Try to find position and sailor name in the data
                            position = None
                            sailor_name = None
                            
                            # Look for position
                            for key in ['pos', 'position', 'place', 'finish']:
                                if key in data:
                                    try:
                                        position = int(data[key])
                                        break
                                    except ValueError:
                                        continue
                            
                            # Look for sailor name
                            for key in ['skipper', 'sailor', 'name', 'competitor']:
                                if key in data:
                                    sailor_name = data[key]
                                    break
                            
                            if sailor_name:
                                # Create or get sailor
                                sailor = self.session.query(Sailor).filter_by(name=sailor_name).first()
                                if not sailor:
                                    sailor = Sailor(
                                        name=sailor_name,
                                        club=data.get('club', data.get('yacht club', '')),
                                        age_category=data.get('category', '')
                                    )
                                    self.session.add(sailor)
                                    self.session.flush()
                                
                                # Create result
                                result = RaceResult(
                                    sailor_id=sailor.id,
                                    race_id=race.id,
                                    position=position,
                                    sail_number=data.get('sail', ''),
                                    boat_name=data.get('boat', ''),
                                    yacht_club=data.get('yacht club', data.get('club', '')),
                                    points=None,  # We can enhance this later
                                    total_points=None
                                )
                                self.session.add(result)
                                print(f"Added result for {sailor_name}")
                        
                        except Exception as e:
                            print(f"Error processing result row: {e}")
                            continue
                    
                    self.session.commit()
                    races.append(race)
                    
                except Exception as e:
                    print(f"Error processing race section: {e}")
                    self.session.rollback()
                    continue
                
        except Exception as e:
            print(f"Error parsing page {url}: {e}")
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
