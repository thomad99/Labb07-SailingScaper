from flask import Flask, render_template, request, jsonify
from chatgpt_scraper import fetch_race_results_from_chatgpt, send_to_db
import os

app = Flask(__name__)

@app.route("/")
def home():
    """Load the HTML frontend."""
    return render_template("index.html")

@app.route("/fetch-results", methods=["POST"])
def fetch_results():
    """Fetch race results from ChatGPT."""
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
def send_to_database():
    """Send validated CSV data to PostgreSQL."""
    data = request.json
    csv_data = data.get("csv_data")

    if not csv_data:
        return jsonify({"error": "No CSV data provided"}), 400

    try:
        response = send_to_db(csv_data)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
