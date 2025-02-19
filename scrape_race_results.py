import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
import threading

db_url = os.getenv("DATABASE_URL")

def scrape_and_store(url, progress_callback):
    try:
        progress_callback("Starting scrape for " + url)
        response = requests.get(url)
        if response.status_code != 200:
            progress_callback("Failed to retrieve the page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        regatta_name = soup.find("h2").text.strip()
        regatta_date = soup.find("h3").text.strip()
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS regatta_results (
                            id SERIAL PRIMARY KEY,
                            regatta_name TEXT,
                            regatta_date TEXT,
                            race_category TEXT,
                            pos INT,
                            sail TEXT,
                            boat TEXT,
                            skipper TEXT,
                            yacht_club TEXT,
                            results TEXT,
                            total_points INT
                         )''')
        conn.commit()
        
        race_categories = soup.find_all("table")
        for table in race_categories:
            headers = [th.text.strip() for th in table.find_all("th")]
            if "Pos" in headers:
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 7:
                        cursor.execute('''INSERT INTO regatta_results 
                                          (regatta_name, regatta_date, race_category, pos, sail, boat, skipper, yacht_club, results, total_points)
                                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                       (regatta_name, regatta_date, headers[0], cols[0].text.strip(), cols[1].text.strip(),
                                        cols[2].text.strip(), cols[3].text.strip(), cols[4].text.strip(), cols[5].text.strip(),
                                        cols[6].text.strip()))
        conn.commit()
        cursor.close()
        conn.close()
        progress_callback("Scraping and storing complete!")
    except Exception as e:
        progress_callback("Error: " + str(e))

app = Flask(__name__)
progress_log = []

def add_progress_message(message):
    progress_log.append(message)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scrape', methods=['POST'])
def start_scrape():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    thread = threading.Thread(target=scrape_and_store, args=(url, add_progress_message))
    thread.start()
    
    return jsonify({"message": "Scraping started"})

@app.route('/get_progress', methods=['GET'])
def get_progress():
    return jsonify({"progress": progress_log})

@app.route('/stop_scrape', methods=['POST'])
def stop_scrape():
    return jsonify({"message": "Stopping scraping is not yet implemented"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
