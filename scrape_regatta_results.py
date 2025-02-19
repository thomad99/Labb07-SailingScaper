import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import traceback

def setup_driver():
    """Setup and return a headless Chrome browser"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def validate_url(url):
    """Validate that the URL is accessible"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Error accessing URL: {e}")
        return False

def parse_result_line(line, category_name):
    """Parse a single result line into a dictionary"""
    try:
        # Match the position number at the start of the line (including tied positions)
        pos_match = re.match(r'^(\d+)\.?\s*', line)
        if not pos_match:
            print(f"No position number found in line: {line}")
            return None
            
        position = pos_match.group(1)
        # Remove the position and period from the start
        data = line[pos_match.end():].strip()
        
        # Split the remaining data by commas and clean each part
        parts = [p.strip() for p in data.split(',')]
        
        # Handle the case where we have fewer parts than expected
        while len(parts) < 6:
            parts.append('')
        
        # Extract total points - handle both formats "; X" and "; XT"
        results_and_points = parts[-1].split(';')
        results = parts[4] if len(parts) > 4 else ''
        total_points = results_and_points[-1].strip() if len(results_and_points) > 1 else parts[-1]
        
        result = {
            'Category': category_name,
            'Position': position,
            'Sail_Number': parts[0],
            'Boat_Name': parts[1] if parts[1] else "No Name",
            'Skipper': parts[2],
            'Yacht_Club': parts[3],
            'Results': results,
            'Total_Points': total_points
        }
        
        print(f"Successfully parsed: Position {position}, {result['Sail_Number']}, {result['Boat_Name']}")
        return result
        
    except Exception as e:
        print(f"Error parsing line '{line}': {str(e)}")
        return None

def scrape_regatta_results(url):
    driver = setup_driver()
    try:
        print("Loading page...")
        driver.get(url)
        time.sleep(2)
        
        all_results = []
        
        # Get the entire page text
        page_text = driver.find_element(By.TAG_NAME, "body").text
        print("Got page text, length:", len(page_text))
        
        # Extract regatta name and date from the first few lines
        lines = page_text.split('\n')
        regatta_name = lines[0].strip() if len(lines) > 0 else "Unknown Regatta"
        regatta_date = ""
        
        # Look for the date line (typically second line)
        for line in lines[1:5]:  # Check first few lines
            if '|' in line:
                date_part = line.split('|')[1].strip()
                regatta_date = date_part
                break
        
        print(f"\nRegatta Name: {regatta_name}")
        print(f"Regatta Date: {regatta_date}")
        
        # Split into sections by looking for category headers
        sections = re.split(r'(\w+\s*\(\d+\s+boats\)\s*\(top\))', page_text)
        print(f"\nFound {len(sections)} sections")
        
        for i in range(1, len(sections), 2):
            if i+1 >= len(sections):
                break
                
            category_header = sections[i]
            category_content = sections[i+1]
            
            # Extract category name
            category_match = re.match(r'(.*?)\s*\((\d+)\s+boats\)', category_header)
            if not category_match:
                print(f"Skipping unmatched header: {category_header}")
                continue
                
            category_name = category_match.group(1).strip()
            num_boats = category_match.group(2)
            print(f"\nProcessing category: {category_name} ({num_boats} boats)")
            
            # Split content into lines
            lines = category_content.split('\n')
            print(f"Found {len(lines)} lines in category")
            
            # Find the results section
            results_started = False
            for line in lines:
                line = line.strip()
                
                # Look for the header line
                if 'Pos,Sail' in line:
                    results_started = True
                    print(f"Found header: {line}")
                    continue
                
                # Process result lines
                if results_started and re.match(r'^\d+\.', line):
                    result = parse_result_line(line, category_name)
                    if result:
                        # Add regatta info to each result
                        result['Regatta_Name'] = regatta_name
                        result['Regatta_Date'] = regatta_date
                        all_results.append(result)
                    else:
                        print(f"Failed to parse line: {line}")
        
        if all_results:
            # Create DataFrame with regatta info first
            columns = ['Regatta_Name', 'Regatta_Date', 'Category', 'Position', 'Sail_Number', 
                      'Boat_Name', 'Skipper', 'Yacht_Club', 'Results', 'Total_Points']
            df = pd.DataFrame(all_results, columns=columns)
            print(f"\nSuccessfully processed {len(all_results)} total results")
            return df
        else:
            print("No results were found")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        traceback.print_exc()
        return pd.DataFrame()
    finally:
        with open('page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("Saved page source to 'page_source.html' for debugging")
        driver.quit()

def clean_results(df):
    if df.empty:
        return df
    
    # Remove leading/trailing whitespace
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].str.strip()
    
    # Clean up Yacht Club names
    club_mappings = {
        'SSS': 'Sarasota Sailing Squadron',
        'Sss': 'Sarasota Sailing Squadron',
        'Sarasota Sailing Squa': 'Sarasota Sailing Squadron'
    }
    
    if 'Yacht_Club' in df.columns:
        df['Yacht_Club'] = df['Yacht_Club'].replace(club_mappings)
    
    return df

def export_results(df, format='csv', output_dir='output'):
    if df.empty:
        print(f"No data to export to {format}")
        return
        
    # Get absolute path for output directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, output_dir)
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
        
    try:
        # Create full file paths
        if format == 'csv':
            output_path = os.path.join(output_dir, 'regatta_results.csv')
            df.to_csv(output_path, index=False)
            print(f"CSV file saved to: {output_path}")
        elif format == 'excel':
            output_path = os.path.join(output_dir, 'regatta_results.xlsx')
            df.to_excel(output_path, index=False)
            print(f"Excel file saved to: {output_path}")
        elif format == 'json':
            output_path = os.path.join(output_dir, 'regatta_results.json')
            df.to_json(output_path, orient='records')
            print(f"JSON file saved to: {output_path}")
    except Exception as e:
        print(f"Error saving {format} file: {str(e)}")
