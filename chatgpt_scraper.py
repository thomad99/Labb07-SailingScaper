from flask import Blueprint, request, jsonify
import openai
import os

# ✅ Define a Flask Blueprint
scraper_bp = Blueprint("scraper", __name__)

# ✅ OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY. Set it in environment variables.")

openai.api_key = OPENAI_API_KEY

def fetch_race_results_from_chatgpt(url):
    """Fetch structured sailing race results from OpenAI and save as CSV."""
    prompt = f"""
    Extract and structure the sailing race data from the following URL: {url}.
    Return the results in a CSV format with the following columns:
    Pos, Sail, Boat, Skipper, Yacht Club, Results, Total Points
    """

    try:
client = openai.OpenAI()  # New way to call OpenAI API

response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[
        {"role": "system", "content": "You are a sailing race data extractor."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=2048
)

        

        csv_data = response["choices"][0]["message"]["content"]

        # ✅ Save CSV to a file
        file_path = "/tmp/output.csv"  # Use /tmp since it's writable on Render
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(csv_data)

        return {
            "prompt": prompt,
            "raw_response": csv_data,
            "csv_data": csv_data,
            "file_path": file_path  # Return the file path
        }
    except Exception as e:
        return {"error": str(e)}

@scraper_bp.route("/fetch-results", methods=["POST"])
def fetch_results():
    """API endpoint to fetch race results from ChatGPT and save CSV."""
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    debug_data = fetch_race_results_from_chatgpt(url)
    return jsonify(debug_data)
