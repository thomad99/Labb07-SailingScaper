from flask import Flask, request, jsonify
from scrape_regatta import scrape_regatta_page
from openai_formatter import format_data_with_gpt
from save_csv import save_to_csv

app = Flask(__name__)

@app.route("/fetch-results", methods=["POST"])
def fetch_results():
    """API endpoint to scrape, format, and save race results to GitHub."""
    data = request.json
    url = data.get("url")

    if not url:
        print("❌ No URL provided!")
        return jsonify({"error": "URL is required"}), 400

    print(f"🔍 Fetching race results from: {url}")

    raw_results = scrape_regatta_page(url)

    if "error" in raw_results:
        print("❌ Error in scraping:", raw_results["error"])
        return jsonify({"error": raw_results["error"]})

    print(f"✅ Extracted {len(raw_results)} rows from webpage")  # ✅ Log data extracted from webpage

    formatted_csv = format_data_with_gpt(raw_results)

    if "Error" in formatted_csv:
        print("❌ OpenAI failed to format data:", formatted_csv)
        return jsonify({"error": formatted_csv})

    print(f"✅ Saving CSV with {len(formatted_csv.splitlines())} rows")  # ✅ Log CSV size

    file_path = save_to_csv(formatted_csv)

    print(f"✅ CSV saved and uploaded to GitHub: {file_path}")

    return jsonify({"message": "Data successfully saved and uploaded!", "file_path": file_path})
