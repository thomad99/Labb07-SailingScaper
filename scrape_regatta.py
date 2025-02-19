import requests
from bs4 import BeautifulSoup

def scrape_regatta_page(url):
    """Scrape the regatta results webpage and extract raw table data."""
    print(f"🔍 Fetching URL: {url}")  # ✅ Log the requested URL

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        print(f"❌ Failed to fetch data. Status code: {response.status_code}")
        return {"error": f"Failed to fetch data. Status code: {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table")
    extracted_data = []

    if not tables:
        print("❌ No tables found on the page!")
        return {"error": "No results tables found."}

    for index, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]

        if not headers:  # Try an alternative method if no <th> found
            first_row = table.find("tr")
            if first_row:
                headers = [td.get_text(strip=True) for td in first_row.find_all("td")]
        
        print(f"🔍 Table {index+1} headers: {headers}")  # ✅ Log detected table headers

        if "Pos" in headers or "Sail" in headers or "Skipper" in headers:
            rows = table.find_all("tr")[1:]  # Skip header row

            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= 5:  # ✅ Adjust the number based on expected columns
                    extracted_data.append(cols)

    print(f"✅ Extracted {len(extracted_data)} race results")  # ✅ Log the extracted results
    return extracted_data
