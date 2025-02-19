import requests
from bs4 import BeautifulSoup
import json

def scrape_regatta_page(url):
    """Scrape the regatta results webpage and extract raw table data."""
    response = requests.get(url)

    if response.status_code != 200:
        return {"error": f"Failed to fetch data. Status code: {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")
    
    tables = soup.find_all("table")
    extracted_data = []

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]

        if "Pos" in headers and "Sail" in headers:
            rows = table.find_all("tr")[1:]

            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= 6:
                    extracted_data.append(cols)

    return extracted_data
