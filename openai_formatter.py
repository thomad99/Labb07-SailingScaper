import openai
import os
import json

# ✅ Initialize OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def format_data_with_gpt(raw_data):
    """Send extracted race data to OpenAI for formatting into CSV."""
    
    if not raw_data:
        print("❌ No data provided for OpenAI to process!")
        return "Error: No data extracted from the webpage"

    print(f"🔍 Sending {len(raw_data)} rows to OpenAI for formatting")  # ✅ Debugging log

    prompt = f"""
    Convert the following sailing race results into a structured CSV format:
    {json.dumps(raw_data, indent=2)}

    Ensure the format:
    Pos, Sail, Boat, Skipper, Yacht Club, Results, Total Points
    """

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a data formatting assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2048
    )

    csv_data = response.choices[0].message.content
    print(f"✅ OpenAI response received ({len(csv_data)} characters)")  # ✅ Debugging log

    return csv_data
