from bs4 import BeautifulSoup
import requests
from datetime import datetime
import time
import os
from database import SessionLocal
from models import Sailor, Race, RaceCategory, RaceResult

# Get environment variables
try:
    from config import SCRAPE_BASE_URL
except ImportError:
    SCRAPE_BASE_URL = os.getenv("SCRAPE_BASE_URL", "https://example-sailing-results.com/results")

class SailingRaceScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = SessionLocal()
        self.progress_log = []
        self.should_stop = False
        self.last_html = None
        self.tables_found = 0
        self.parse_errors = []

    def add_progress_message(self, message):
        print(message)  # Print to console for debugging
        self.progress_log.append(message)

    def scrape_and_store(self):
        try:
            self.add_progress_message(f"Starting scrape for {self.base_url}")
            
            # Add headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(self.base_url, headers=headers)
            if response.status_code != 200:
                self.add_progress_message(f"Failed to retrieve the page: {response.status_code}")
                return
            
            self.last_html = response.text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find regatta details
            regatta_name = "Cherry Pie Regatta"  # Default name
            regatta_date = datetime(2025, 2, 15)  # Default date
            
            h2_tag = soup.find("h2")
            if h2_tag:
                regatta_name = h2_tag.text.strip()
            
            h3_tag = soup.find("h3")
            if h3_tag and "date" in h3_tag.text.lower():
                regatta_date = self.parse_date(h3_tag.text.strip())
            
            self.add_progress_message(f"Processing {regatta_name} on {regatta_date}")
            
            # Find all result tables
            tables = soup.find_all("table")
            self.tables_found = len(tables)
            self.add_progress_message(f"Found {len(tables)} result tables")
            
            total_results = 0
            categories_found = set()
            
            for table in tables:
                try:
                    # Get category name from preceding header
                    category_header = table.find_previous('h2')
                    category_name = category_header.text.strip() if category_header else "Unknown Category"
                    categories_found.add(category_name)
                    
                    # Create or get category
                    category = self.session.query(RaceCategory).filter_by(name=category_name).first()
                    if not category:
                        category = RaceCategory(name=category_name)
                        self.session.add(category)
                        self.session.flush()
                    
                    # Process table rows
                    rows = table.find_all("tr")[1:]  # Skip header row
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 7:
                            # Extract data from columns
                            pos = int(cols[0].text.strip().split('.')[0])
                            sail = cols[1].text.strip()
                            boat = cols[2].text.strip()
                            skipper = cols[3].text.strip()
                            club = cols[4].text.strip()
                            race_results = cols[5].text.strip()
                            points = float(cols[6].text.strip().split()[0])
                            
                            # Create or get sailor
                            sailor = self.session.query(Sailor).filter_by(name=skipper).first()
                            if not sailor:
                                sailor = Sailor(name=skipper, club=club)
                                self.session.add(sailor)
                                self.session.flush()
                            
                            # Create race results
                            race_numbers = race_results.split('-')[:-1]  # Split and remove empty last element
                            for i, result in enumerate(race_numbers, 1):
                                race = Race(
                                    name=f"{regatta_name} - {category_name} - Race {i}",
                                    date=regatta_date,
                                    venue="Sarasota Sailing Squadron",
                                    category_id=category.id,
                                    event_name=regatta_name
                                )
                                self.session.add(race)
                                self.session.flush()
                                
                                # Parse result
                                dnf = 'DNF' in result
                                dns = 'DNS' in result
                                
                                race_result = RaceResult(
                                    sailor_id=sailor.id,
                                    race_id=race.id,
                                    position=pos,
                                    sail_number=sail,
                                    boat_name=boat,
                                    yacht_club=club,
                                    points=points,
                                    total_points=points,
                                    dnf=dnf,
                                    dns=dns
                                )
                                self.session.add(race_result)
                                total_results += 1
                            
                    self.session.commit()
                    
                except Exception as e:
                    self.add_progress_message(f"Error processing table: {str(e)}")
                    self.session.rollback()
                    continue
            
            self.add_progress_message(f"Scraping complete! Processed {total_results} results in {len(categories_found)} categories")
            return {
                'total_results': total_results,
                'categories': list(categories_found)
            }
            
        except Exception as e:
            self.add_progress_message(f"Error: {str(e)}")
            return None
        finally:
            self.session.close()

    def parse_date(self, date_string):
        formats = ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        return datetime(2025, 2, 15)  # Default date if parsing fails

    def scrape_all_results(self):
        """Main entry point for scraping"""
        start_time = time.time()
        result = self.scrape_and_store()
        elapsed_time = time.time() - start_time
        
        return {
            'url_processed': self.base_url,
            'total_races': result['total_results'] if result else 0,
            'total_results': result['total_results'] if result else 0,
            'categories': result['categories'] if result else [],
            'elapsed_time': f"{elapsed_time:.1f} seconds",
            'stop_reason': "Completed",
            'debug_info': {
                'html_length': len(self.last_html) if self.last_html else 0,
                'tables_found': self.tables_found,
                'parse_errors': self.parse_errors,
                'progress_log': self.progress_log
            }
        }

if __name__ == "__main__":
    scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    scraper.scrape_all_results() 
