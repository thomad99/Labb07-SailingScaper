import os
import openai
import csv
import io
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Get OpenAI API Key from Environment Variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API Key. Set OPENAI_API_KEY in environment.")

openai.api_key = OPENAI_API_KEY

def fetch_race_results_from_chatgpt(url):
    """Fetch structured sailing race results from ChatGPT."""
    prompt = f"""
    Extract and structure the sailing race data from the following URL: {url}.

    The structured data should include:
    - Regatta Name
    - Regatta Date
    - Race Categories (e.g., Sunfish, M15)
    - Results for each category in a CSV format:
      Pos, Sail, Boat, Skipper, Yacht Club, Results, Total Points

    Ensure the data is cleaned and formatted correctly.
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
    """Fetch race results from OpenAI and return CSV data."""
    try:
        data = request.json
        url = data.get("url")

        if not url:
            return jsonify({"error": "Missing URL"}), 400

        csv_data = fetch_race_results_from_chatgpt(url)

        if not csv_data:
            return jsonify({"error": "No data received from OpenAI"}), 500

        return jsonify({"csv_data": csv_data})

    except Exception as e:
        print(f"🚨 ERROR: {str(e)}")  # Logs error to Render
        return jsonify({"error": str(e)}), 500
@app.route("/send-to-db", methods=["POST"])
def send_to_db():
    """Store validated CSV data into PostgreSQL."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Race, RaceResult  # Ensure models are set up

    data = request.json
    csv_data = data.get("csv_data")

    if not csv_data:
        return jsonify({"error": "No CSV data provided"}), 400

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Read CSV data
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
