from bs4 import BeautifulSoup
import requests
from datetime import datetime
import time
from urllib.parse import urljoin, urlparse
import os
from database import SessionLocal
from models import Sailor, Race, RaceCategory, RaceResult

# Try to import from config, fall back to environment variables if config is missing
try:
    from config import SCRAPE_BASE_URL
except ImportError:
    SCRAPE_BASE_URL = os.getenv("SCRAPE_BASE_URL", "https://example-sailing-results.com/results")

class SailingRaceScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls = set()
        self.session = SessionLocal()
        self.should_stop = False
        self.max_pages = 100
        self.timeout = 3600
        self.start_time = None
        self.last_html = None
        self.tables_found = 0
        self.parse_errors = []

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
            
            # Add more headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print(f"\nFetching URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Response status code: {response.status_code}")
            
            # Store the HTML for debugging
            self.last_html = response.text
            print(f"Response length: {len(self.last_html)}")
            print("\nFirst 500 characters of response:")
            print(self.last_html[:500])
            
            response.raise_for_status()
            self.visited_urls.add(url)
            
            # Initialize debug counters
            self.tables_found = 0
            self.parse_errors = []
            
            return response.text
            
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            self.parse_errors.append(f"Request error: {str(e)}")
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
        if not html:
            self.parse_errors.append("No HTML content received")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        races = []
        
        try:
            print("\n=== Page Content Analysis ===")
            print(f"URL being processed: {url}")
            
            # Find all tables
            tables = soup.find_all('table')
            self.tables_found = len(tables)
            print(f"\nFound {self.tables_found} tables")
            
            if not tables:
                print("\nHTML Structure:")
                print(soup.prettify()[:1000])
                self.parse_errors.append("No tables found in HTML")
                return races
            
            # Process each table that looks like results
            for table in tables:
                try:
                    # Print table structure for debugging
                    print("\nTable HTML:")
                    print(table.prettify()[:500])
                    
                    # Check if this is a results table by looking at first row
                    first_row = table.find('tr')
                    if not first_row:
                        print("No rows in table")
                        continue
                    
                    cells = first_row.find_all(['td', 'th'])
                    print(f"\nFirst row cells ({len(cells)}):")
                    for i, cell in enumerate(cells):
                        print(f"Cell {i}: {cell.text.strip()}")
                    
                    # Get the category name from preceding h2
                    category_header = table.find_previous('h2')
                    if category_header:
                        category_name = category_header.text.strip().split('(')[0].strip()
                        print(f"\nProcessing category: {category_name}")
                        
                        # Create or get category
                        category = self.session.query(RaceCategory).filter_by(name=category_name).first()
                        if not category:
                            category = RaceCategory(name=category_name)
                            self.session.add(category)
                            self.session.flush()
                        
                        # Create three races for this category (since there are three results per boat)
                        base_race_name = "Cherry Pie Regatta"
                        race_date = datetime(2025, 2, 15)
                        
                        races_in_series = []
                        for i in range(1, 4):  # Create 3 races
                            race = Race(
                                name=f"{base_race_name} - {category_name} - Race {i}",
                                date=race_date,
                                venue="Sarasota Sailing Squadron",
                                category_id=category.id,
                                event_name=base_race_name
                            )
                            self.session.add(race)
                            self.session.flush()
                            races_in_series.append(race)
                            races.append(race)
                        
                        # Process each row of results
                        for row in table.find_all('tr')[1:]:  # Skip header row
                            cells = row.find_all('td')
                            if len(cells) < 6:  # Need at least position, sail, boat, skipper, club, results
                                continue
                            
                            try:
                                # Extract basic data
                                position = int(cells[0].text.strip().split('.')[0])
                                sail_number = cells[1].text.strip()
                                boat_name = cells[2].text.strip()
                                skipper_name = cells[3].text.strip()
                                yacht_club = cells[4].text.strip()
                                
                                # Parse race results (format: "1-1-1-")
                                results_text = cells[5].text.strip()
                                race_results = results_text.split('-')[:-1]  # Split and remove empty last element
                                total_points = float(cells[6].text.strip().split()[0])  # Format: "3 T" or just "3"
                                
                                print(f"\nProcessing: {sail_number} - {skipper_name} - Results: {race_results}")
                                
                                # Create or get sailor
                                sailor = self.session.query(Sailor).filter_by(name=skipper_name).first()
                                if not sailor:
                                    sailor = Sailor(
                                        name=skipper_name,
                                        club=yacht_club
                                    )
                                    self.session.add(sailor)
                                    self.session.flush()
                                
                                # Add results for each race
                                for race_num, (race, result) in enumerate(zip(races_in_series, race_results)):
                                    # Parse the result
                                    dnf = 'DNF' in result
                                    dns = 'DNS' in result
                                    dnc = 'DNC' in result
                                    
                                    # Get position or max position for DNF/DNS/DNC
                                    if dnf or dns or dnc:
                                        race_position = 8  # From the data, seems to be max position
                                    else:
                                        race_position = int(result)
                                    
                                    result = RaceResult(
                                        sailor_id=sailor.id,
                                        race_id=race.id,
                                        position=race_position,
                                        sail_number=sail_number,
                                        boat_name=boat_name,
                                        yacht_club=yacht_club,
                                        points=float(result.split('/')[0]) if '/' in result else float(result),
                                        total_points=total_points,
                                        dnf=dnf,
                                        dns=dns
                                    )
                                    self.session.add(result)
                                    print(f"Added result for race {race_num + 1}: Position {race_position}")
                                
                            except Exception as e:
                                error_msg = f"Error processing row: {str(e)}"
                                print(error_msg)
                                self.parse_errors.append(error_msg)
                                continue
                        
                        self.session.commit()
                        
                except Exception as e:
                    error_msg = f"Error processing table: {str(e)}"
                    print(error_msg)
                    self.parse_errors.append(error_msg)
                    continue
                
        except Exception as e:
            error_msg = f"Error parsing page: {str(e)}"
            print(error_msg)
            self.parse_errors.append(error_msg)
        
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
            'stop_reason': stop_reason,
            'tables_found': self.tables_found,
            'parse_errors': self.parse_errors
        }

if __name__ == "__main__":
    scraper = SailingRaceScraper(SCRAPE_BASE_URL)
    scraper.scrape_all_results() 
