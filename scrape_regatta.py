import os
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# ✅ Define a reliable Chromium binary location
CHROMIUM_PATH = "/usr/local/bin/chrome-linux/chrome"
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"

def install_chromium():
    """Download and configure a portable Chromium binary for Selenium."""
    if not os.path.exists(CHROMIUM_PATH):
        print("🔧 Downloading Chromium Portable...")

        # ✅ Download and extract a stable Chromium version
        subprocess.run(
            "wget -q https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.128/linux64/chrome-linux.zip -O /tmp/chrome.zip",
            shell=True,
            check=True,
        )
        subprocess.run("unzip /tmp/chrome.zip -d /usr/local/bin/", shell=True, check=True)
        print("✅ Chromium installed successfully!")

def scrape_regatta_page(url):
    """Use Selenium to scrape dynamically loaded race results."""
    print(f"🔍 Fetching URL: {url} using Selenium")

    # ✅ Install Chromium if not found
    install_chromium()

    # ✅ Set up Selenium WebDriver with the portable Chromium
    options = Options()
    options.add_argument("--headless")  # Run without UI
    options.add_argument("--no-sandbox")  # Required for Render/Docker environments
    options.add_argument("--disable-dev-shm-usage")  # Prevent crashes
    options.binary_location = CHROMIUM_PATH  # ✅ Use the manually installed Chromium

    # ✅ Use the correct ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

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
