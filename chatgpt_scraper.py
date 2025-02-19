from flask import Flask, request, jsonify
import openai
import os
import csv
import io
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import RaceResult  # Ensure your database models are properly set up

app = Flask(__name__)

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API Key. Set OPENAI_API_KEY in environment.")
openai.api_key = OPENAI_API_KEY

# Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL. Set it in Render environment variables.")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def fetch_race_results_from_chatgpt(url):
    """Fetch structured sailing race results from ChatGPT."""
    prompt = f"""
    Extract and structure the sailing race data from the following URL: {url}.
    Return the results in a CSV format with the following columns:
    Pos, Sail, Boat, Skipper, Yacht Club, Results, Total Points
    """

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are a sailing race data extractor."},
                  {"role": "user", "content": prompt}],
        max_tokens=2048
    )

    return response["choices"][0]["message"]["content"]

@app.route("/fetch-results", methods=["POST"])
def fetch_results():
    """API to fetch race results from ChatGPT and return CSV."""
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        csv_data = fetch_race_results_from_chatgpt(url)
        return jsonify({"csv_data": csv_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/send-to-db", methods=["POST"])
def send_to_db():
    """API to store validated CSV data into PostgreSQL."""
    data = request.json
    csv_data = data.get("csv_data")

    if not csv_data:
        return jsonify({"error": "No CSV data provided"}), 400

    session = Session()
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        for row in csv_reader:
            race_result = RaceResult(
                position=int(row["Pos"]),
                sail_number=row["Sail"],
                boat_name=row["Boat"],
                skipper=row["Skipper"],
                yacht_club=row["Yacht Club"],
                results=row["Results"],
                total_points=int(row["Total Points"])
            )
            session.add(race_result)

        session.commit()
        return jsonify({"message": "Data successfully stored in database."})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)})
    finally:
        session.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
