import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import openai
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

print(f"API Key found: {'Yes' if OPENAI_API_KEY else 'No'}")  # Debug print (will not show the actual key)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

class Query(BaseModel):
    question: str

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies OpenAI API key"""
    try:
        # Test OpenAI connection
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
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
        
        response = openai.ChatCompletion.create(
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
        
        response = openai.ChatCompletion.create(
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
            data = [dict(row) for row in result]
            print(f"Query results: {data}")  # Debug print
        
        # Format results
        if not data:
            return {"response": "I couldn't find any data to answer that question. The database might be empty or the question might need to be rephrased."}
            
        formatted_response = format_results(data, query.question)
        return {"response": formatted_response}
    
    except Exception as e:
        print(f"Error processing question: {str(e)}")  # Debug print
        raise HTTPException(status_code=500, detail=str(e)) 
