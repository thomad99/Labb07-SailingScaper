from flask import Flask, request, jsonify, send_file
import os
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

    # Step 1: Scrape webpage
    raw_results = scrape_regatta_page(url)

    if "error" in raw_results:
        return jsonify({"error": raw_results["error"]})

    # Step 2: Format with OpenAI
    formatted_csv = format_data_with_gpt(raw_results)

    # Step 3: Save as CSV file
    file_path = save_to_csv(formatted_csv)

    return jsonify({"message": "Data successfully saved!", "file_path": file_path})

@app.route("/download-results", methods=["GET"])
def download_results():
    """API endpoint to download the saved CSV file."""
    file_path = "/tmp/regatta_results.csv"

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name="race_results.csv")
    else:
        return jsonify({"error": "No CSV file found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
