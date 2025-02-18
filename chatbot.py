from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import openai
from typing import Optional
import os

app = FastAPI()

# Configure database
DB_URL = "postgresql://username:password@localhost:5432/sailing_results"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

class Query(BaseModel):
    question: str

def generate_sql_query(question: str) -> str:
    """Use OpenAI to generate SQL query from natural language"""
    prompt = f"""
    Given the following database schema:
    - sailors (id, name, club, age_category)
    - races (id, name, date, venue)
    - race_results (id, sailor_id, race_id, position, finish_time, boat_name)

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
    
    return response.choices[0].message.content.strip()

def format_results(results: list, question: str) -> str:
    """Use OpenAI to format results in natural language"""
    prompt = f"""
    Question: {question}
    Raw results: {results}
    
    Please format these results in a natural, friendly way that answers the question.
    Use bullet points where appropriate.
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant who explains sailing race results clearly."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()

@app.post("/ask")
async def ask_question(query: Query):
    try:
        # Generate SQL query
        sql_query = generate_sql_query(query.question)
        
        # Execute query
        with SessionLocal() as db:
            result = db.execute(text(sql_query))
            data = [dict(row) for row in result]
        
        # Format results
        formatted_response = format_results(data, query.question)
        
        return {"response": formatted_response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))chatbot.py
