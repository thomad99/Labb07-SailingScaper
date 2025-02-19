import os
import openai
import csv
import requests
from flask import Flask, request, jsonify, render_template
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class RegattaResult(Base):
    __tablename__ = "regatta_results"
    id = Column(Integer, primary_key=True, index=True)
    regatta_name = Column(String, index=True)
    regatta_date = Column(String, index=True)
    race_category = Column(String, index=True)
    pos = Column(Integer)
    sail = Column(String)
    boat = Column(String)
    skipper = Column(String)
    yacht_club = Column(String)
    results = Column(Text)
    total_points = Column(Integer)

Base.metadata.create_all(bind=engine)

app = Flask(__name__)

def fetch_race_data(url):
    prompt = f"""
    Extract and structure the sailing race data from the following URL: {url}
    Output the data in CSV format with the following columns:
    regatta_name, regatta_date, race_category, pos, sail, boat, skipper, yacht_club, results, total_points.
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are an assistant that extracts structured data from web pages."},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape_chatgpt', methods=['POST'])
def scrape_chatgpt():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    csv_data = fetch_race_data(url)
    return jsonify({"csv_data": csv_data})

@app.route('/send_to_db', methods=['POST'])
def send_to_db():
    data = request.json
    csv_text = data.get("csv_data")
    if not csv_text:
        return jsonify({"error": "CSV data is required"}), 400
    
    session = SessionLocal()
    reader = csv.reader(csv_text.splitlines())
    headers = next(reader)  # Skip header row
    
    for row in reader:
        result = RegattaResult(
            regatta_name=row[0],
            regatta_date=row[1],
            race_category=row[2],
            pos=int(row[3]),
            sail=row[4],
            boat=row[5],
            skipper=row[6],
            yacht_club=row[7],
            results=row[8],
            total_points=int(row[9])
        )
        session.add(result)
    session.commit()
    session.close()
    
    return jsonify({"message": "Data successfully saved to the database"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
