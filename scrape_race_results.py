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
                
                # ... rest of the parsing code ...

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
