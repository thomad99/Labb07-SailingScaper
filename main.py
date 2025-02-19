from flask import Flask, request, jsonify, send_file
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

    file_path = save_csv(formatted_csv)  # ✅ Saves locally and pushes to GitHub

    return jsonify({"message": "Data successfully saved and uploaded!", "file_path": file_path})

@app.route("/download-results", methods=["GET"])
def download_results():
    """Endpoint to allow users to download the generated CSV file."""
    if os.path.exists(CSV_FILE_PATH):
        return send_file(CSV_FILE_PATH, as_attachment=True, download_name="race_results.csv")
    else:
        return jsonify({"error": "No CSV file found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
