from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, text
import os

app = Flask(__name__)

# ✅ Get DATABASE_URL securely from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL. Set it in Render environment variables.")

# ✅ Create a database engine for PostgreSQL
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# ✅ Import Blueprint from chatgpt_scraper
from chatgpt_scraper import scraper_bp  

# ✅ Register Blueprint for scraper routes
app.register_blueprint(scraper_bp, url_prefix="/api")  # All API calls will be prefixed with /api

@app.route("/")
def home():
    """Load the main frontend."""
    return render_template("index.html")

@app.route("/query-db", methods=["POST"])
def query_database():
    """Handle database queries securely."""
    data = request.json
    user_query = data.get("query", "").lower()

    with engine.connect() as conn:
        if "results for sailor" in user_query:
            sailor_name = user_query.split("results for sailor")[-1].strip()
            sql = text("SELECT * FROM race_results WHERE skipper ILIKE :sailor_name")
            result = conn.execute(sql, {"sailor_name": f"%{sailor_name}%"}).fetchall()
        
        elif "results for" in user_query and "team" in user_query:
            team_name = user_query.split("results for the")[-1].strip().split("team")[0].strip()
            sql = text("SELECT * FROM race_results WHERE yacht_club ILIKE :team_name ORDER BY id DESC LIMIT 5")
            result = conn.execute(sql, {"team_name": f"%{team_name}%"}).fetchall()
        
        else:
            return jsonify({"answer": "Sorry, I didn't understand. Try asking about a sailor or a team."})

        if not result:
            return jsonify({"answer": "No results found for your query."})

        formatted_results = "\n".join(
            [f"🏅 {row['skipper']} ({row['yacht_club']}): {row['results']} - {row['total_points']} points" for row in result]
        )

        return jsonify({"answer": formatted_results})

@app.route("/chatbot")
def chatbot():
    """Load the chatbot interface."""
    return render_template("chatbot.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
