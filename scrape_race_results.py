from bs4 import BeautifulSoup
import requests
import pandas as pd
from datetime import datetime
import time
import json
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class Sailor(Base):
    __tablename__ = 'sailors'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    club = Column(String)
    age_category = Column(String)
    results = relationship("RaceResult", back_populates="sailor")

class Race(Base):
    __tablename__ = 'races'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    date = Column(DateTime)
    venue = Column(String)
    results = relationship("RaceResult", back_populates="race")

class RaceResult(Base):
    __tablename__ = 'race_results'
    id = Column(Integer, primary_key=True)
    sailor_id = Column(Integer, ForeignKey('sailors.id'))
    race_id = Column(Integer, ForeignKey('races.id'))
    position = Column(Integer)
    finish_time = Column(Float)  # Store as seconds for easy comparison
    boat_name = Column(String)
    
    sailor = relationship("Sailor", back_populates="results")
    race = relationship("Race", back_populates="results")

class SailingRaceScraper:
    def __init__(self, base_url, db_url):
        self.base_url = base_url
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_page(self, url):
        """Fetch page content with error handling and rate limiting"""
        try:
            # Add delay to be respectful to the server
            time.sleep(1)
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_race_results(self, html):
        """Parse race results from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # You'll need to customize these selectors based on the website structure
        for race_elem in soup.find_all('div', class_='race-result'):
            # Create Race entry
            race = Race(
                name=race_elem.find('h2', class_='race-name').text.strip(),
                date=datetime.strptime(race_elem.find('span', class_='date').text.strip(), '%Y-%m-%d'),
                venue=race_elem.find('span', class_='venue').text.strip()
            )
            self.session.add(race)
            self.session.flush()  # To get race.id
            
            # Parse participant results
            for participant in race_elem.find_all('div', class_='participant'):
                # Get or create sailor
                sailor_name = participant.find('span', class_='skipper').text.strip()
                sailor = self.session.query(Sailor).filter_by(name=sailor_name).first()
                if not sailor:
                    sailor = Sailor(
                        name=sailor_name,
                        club=participant.find('span', class_='club').text.strip(),
                        age_category=participant.find('span', class_='category').text.strip()
                    )
                    self.session.add(sailor)
                    self.session.flush()
                
                # Create race result
                result = RaceResult(
                    sailor_id=sailor.id,
                    race_id=race.id,
                    position=int(participant.find('span', class_='position').text.strip()),
                    finish_time=self.parse_time_to_seconds(participant.find('span', class_='time').text.strip()),
                    boat_name=participant.find('span', class_='boat-name').text.strip()
                )
                self.session.add(result)
            
            self.session.commit()

    def parse_time_to_seconds(self, time_str):
        """Convert time string (HH:MM:SS) to seconds"""
        try:
            time_parts = time_str.split(':')
            if len(time_parts) == 3:
                hours, minutes, seconds = map(float, time_parts)
                return hours * 3600 + minutes * 60 + seconds
            return None
        except:
            return None

    def scrape_all_results(self):
        """Main function to scrape all race results"""
        html = self.get_page(self.base_url)
        if html:
            self.parse_race_results(html)

if __name__ == "__main__":
    db_url = "postgresql://username:password@localhost:5432/sailing_results"
    scraper = SailingRaceScraper('https://example-sailing-results.com', db_url)
    scraper.scrape_all_results() 
