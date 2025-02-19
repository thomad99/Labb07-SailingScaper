import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from openai import OpenAI  # Import the client class
from typing import Optional
from database import engine, SessionLocal

app = FastAPI()

# Get environment variables with better error handling
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found in environment variables")
    try:
        from config import OPENAI_API_KEY
    except ImportError:
        raise ValueError("OPENAI_API_KEY not found in environment or config")

print(f"API Key found: {'Yes' if OPENAI_API_KEY else 'No'}")  # Debug print

# Initialize OpenAI client with minimal configuration
client = OpenAI(api_key=OPENAI_API_KEY)

# Test the connection
try:
    test_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "test"}]
    )
    print("OpenAI connection test successful")
except Exception as e:
    print(f"OpenAI connection test failed: {str(e)}")
    raise

class Query(BaseModel):
    question: str

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies OpenAI API key"""
    try:
        # Test OpenAI connection
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}]
        )
        return {
            "status": "healthy",
            "openai_connected": True,
            "database_connected": True
        }
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def generate_sql_query(question: str) -> str:
    """Use OpenAI to generate SQL query from natural language"""
    try:
        prompt = f"""
        Given the following database schema:
        - sailors (id, name, club, age_category)
        - race_categories (id, name)
        - races (id, name, date, venue, category_id, event_name)
        - race_results (id, sailor_id, race_id, position, sail_number, boat_name, yacht_club, points, total_points, dnf, dns)

        Generate a SQL query to answer this question: {question}
        Return only the SQL query, nothing else.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a SQL expert. Generate only SQL queries, no explanations."},
                {"role": "user", "content": prompt}
            ]
        )
        
        sql = response.choices[0].message.content.strip()
        print(f"Generated SQL: {sql}")  # Debug print
        return sql
        
    except Exception as e:
        print(f"Error generating SQL: {str(e)}")
        raise

def format_results(results: list, question: str) -> str:
    """Use OpenAI to format results in natural language"""
    try:
        prompt = f"""
        Question: {question}
        Raw results: {results}
        
        Please format these results in a natural, friendly way that answers the question.
        Use bullet points where appropriate.
        If there are no results, please say that no data was found.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who explains sailing race results clearly."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error formatting results: {str(e)}")
        raise

@app.post("/ask")
async def ask_question(query: Query):
    try:
        print(f"\nReceived question: {query.question}")  # Debug print
        
        # Generate SQL query
        sql_query = generate_sql_query(query.question)
        
        # Execute query
        with SessionLocal() as db:
            result = db.execute(text(sql_query))
            
            # Handle different result types
            if sql_query.lower().strip().startswith('select count'):
                # For COUNT queries, get the single value
                data = [{"count": result.scalar()}]
            else:
                # For other queries, get all rows as dictionaries
                data = [dict(zip(result.keys(), row)) for row in result]
            
            print(f"Query results: {data}")  # Debug print
        
        # Format results
        if not data:
            return {"response": "I couldn't find any data to answer that question. The database might be empty or the question might need to be rephrased."}
            
        formatted_response = format_results(data, query.question)
        return {"response": formatted_response}
    
    except Exception as e:
        print(f"Error processing question: {str(e)}")  # Debug print
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test_connection():
    """Test endpoint to verify database connection and show basic stats"""
    try:
        with SessionLocal() as db:
            # Get basic counts
            stats = {
                "sailors": db.execute(text("SELECT COUNT(*) FROM sailors")).scalar(),
                "races": db.execute(text("SELECT COUNT(*) FROM races")).scalar(),
                "results": db.execute(text("SELECT COUNT(*) FROM race_results")).scalar(),
                "categories": db.execute(text("SELECT COUNT(*) FROM race_categories")).scalar()
            }
            
            # Get sample data
            recent_races = db.execute(text("""
                SELECT name, date::text, venue 
                FROM races 
                ORDER BY date DESC 
                LIMIT 3
            """)).fetchall()
            
            # Get categories with counts
            categories = db.execute(text("""
                SELECT rc.name, COUNT(r.id) as race_count
                FROM race_categories rc
                LEFT JOIN races r ON rc.id = r.category_id
                GROUP BY rc.name
                ORDER BY race_count DESC
            """)).fetchall()
            
            return {
                "status": "connected",
                "database_stats": stats,
                "recent_races": [dict(r) for r in recent_races],
                "categories": [dict(c) for c in categories],
                "message": "Database connection successful"
            }
            
    except Exception as e:
        print(f"Database test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to connect to database"
        } 
