from pymongo import MongoClient
import pandas as pd

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["aviation_dashboard"]

# Clear old collections
db.flights.drop()
db.weather.drop()
db.delays.drop()

# Read Excel Files
flights = pd.read_excel("data/flights.xlsx", engine="openpyxl")
weather = pd.read_excel("data/weather.xlsx", engine="openpyxl")
delays = pd.read_excel("data/delays.xlsx", engine="openpyxl")

# Convert all columns to string
flights = flights.astype(str)
weather = weather.astype(str)
delays = delays.astype(str)

# Convert to dictionaries
flight_records = flights.to_dict("records")
weather_records = weather.to_dict("records")
delay_records = delays.to_dict("records")

# Insert into MongoDB
if flight_records:
    db.flights.insert_many(flight_records)

if weather_records:
    db.weather.insert_many(weather_records)

if delay_records:
    db.delays.insert_many(delay_records)

print("Flights imported successfully")
print("Weather imported successfully")
print("Delays imported successfully")