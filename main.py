from flask import Flask, request, jsonify
from scrape_regatta import scrape_regatta_page
from openai_formatter import format_data_with_gpt
from save_csv import save_to_csv

app = Flask(__name__)

@app.route("/fetch-results", methods=["POST"])
def fetch_results():
    """API endpoint to scrape, format, and save race results."""
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    raw_results = scrape_regatta_page(url)

    if "error" in raw_results:
        return jsonify({"error": raw_results["error"]})

    formatted_csv = format_data_with_gpt(raw_results)

    file_path = save_to_csv(formatted_csv)  # ✅ Saves locally and pushes to GitHub

    return jsonify({"message": "Data successfully saved and uploaded!", "file_path": file_path})
