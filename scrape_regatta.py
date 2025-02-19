import requests
from bs4 import BeautifulSoup

def scrape_regatta_page(url):
    """Scrape the regatta results webpage and extract raw table data."""
    print(f"🔍 Fetching URL: {url}")  # ✅ Log the requested URL

    response = requests.get(url)

    if response.status_code != 200:
        print(f"❌ Failed to fetch data. Status code: {response.status_code}")
        return {"error": f"Failed to fetch data. Status code: {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table")
    extracted_data = []

    if not tables:
        print("❌ No tables found on the page!")
        return {"error": "No results tables found."}

    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        print(f"🔍 Found table with headers: {headers}")  # ✅ Log detected table headers

        if "Pos" in headers and "Sail" in headers:  # Detect race results table
            rows = table.find_all("tr")[1:]  # Skip header row

            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= 6:
                    extracted_data.append(cols)

    print(f"✅ Extracted {len(extracted_data)} race results")  # ✅ Log the extracted results
    return extracted_data
