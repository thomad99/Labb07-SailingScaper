from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

def scrape_regatta_page(url):
    """Use Selenium to scrape dynamically loaded race results."""
    print(f"🔍 Fetching URL: {url} using Selenium")

    # ✅ Set up Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run without opening a browser
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    driver.get(url)
    time.sleep(5)  # ✅ Wait for JavaScript to load

    page_html = driver.page_source
    driver.quit()  # ✅ Close the browser

    # ✅ Parse the full page HTML with BeautifulSoup
    soup = BeautifulSoup(page_html, "html.parser")

    tables = soup.find_all("table")
    extracted_data = []

    if not tables:
        print("❌ No tables found on the page!")
        return {"error": "No results tables found."}

    for index, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]

        print(f"🔍 Table {index+1} headers: {headers}")

        if "Pos" in headers or "Sail" in headers or "Skipper" in headers:
            rows = table.find_all("tr")[1:]  # Skip header row

            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= 5:
                    extracted_data.append(cols)

    print(f"✅ Extracted {len(extracted_data)} race results")
    return extracted_data
