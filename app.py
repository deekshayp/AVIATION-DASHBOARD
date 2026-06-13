from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient, DESCENDING
import math
import random
from datetime import datetime

app = Flask(__name__)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["aviation_dashboard"]

@app.route("/api/dashboard")
def dashboard():

    flights = list(db.flights.find({}, {"_id": 0}))
    weather_data = list(db.weather.find({}, {"_id": 0}))
    runways = list(db.runways.find({}, {"_id": 0}))

    weather_map = {}

    for w in weather_data:
        weather_map[w["airport"]] = w

    
    enriched_flights = []

    for flight in flights:

        origin = flight["origin"]

        weather = weather_map.get(flight["origin"], {})
        condition = weather.get("label", "Unknown")

        delay = calculate_delay(condition)

        flight["origin_weather"] = condition
        if flight.get("status", "Scheduled") == "Delayed":
            delay = flight.get("delay_minutes", 15)

        else:
            delay = calculate_delay(
                flight["origin_weather"]
            )

        risk_score = calculate_risk_score(condition, delay)

        flight["risk_score"] = risk_score

        if risk_score < 30:
            flight["risk_level"] = "Low"

        elif risk_score < 70:
            flight["risk_level"] = "Medium"

        else:
            flight["risk_level"] = "High"
        flight["delay_prediction"] = f"{delay} min"

        flight["delay_reason"] = flight.get(
            "delay_reason",
            "Weather"
        )

        enriched_flights.append(flight)

    return jsonify({
        "flights": enriched_flights,
        "runways": runways,
        "weather": weather_data
    })

flights_col = db["flights"]
weather_col = db["weather_updates"]
runways_col = db["runways"]
logs_col = db["flight_logs"]

AIRPORTS = {
    "BLR": {"name":"Bengaluru", "lat":12.9716, "lon":77.5946},
    "DEL": {"name":"Delhi", "lat":28.6139, "lon":77.2090},
    "BOM": {"name":"Mumbai", "lat":19.0760, "lon":72.8777},
    "MAA": {"name":"Chennai", "lat":13.0827, "lon":80.2707},
    "HYD": {"name":"Hyderabad", "lat":17.3850, "lon":78.4867},
    "CCU": {"name":"Kolkata", "lat":22.5726, "lon":88.3639},

    "NAGPUR": {"name":"Nagpur", "lat":21.1458, "lon":79.0882},
    "PUNE": {"name":"Pune", "lat":18.5204, "lon":73.8567},
    "GOA": {"name":"Goa", "lat":15.2993, "lon":74.1240},
    "VARANASI": {"name":"Varanasi", "lat":25.3176, "lon":82.9739},
    "BHUBANESWAR": {"name":"Bhubaneswar", "lat":20.2961, "lon":85.8245}
}

ROUTES = [
    ("DEL", "DXB"), ("DEL", "BOM"), ("DEL", "CDG"), ("DEL", "LHR"),
    ("DXB", "LHR"), ("DXB", "SIN"), ("DXB", "CDG"), ("DXB", "BOM"),
    ("LHR", "CDG"), ("LHR", "JFK"),
    ("CDG", "JFK"),
    ("JFK", "HND"), ("JFK", "LHR"),
    ("SIN", "HKG"), ("SIN", "SYD"), ("SIN", "HND"),
    ("HKG", "HND"), ("HKG", "SYD"), ("HKG", "JFK"),
    ("HND", "JFK"),
    ("BOM", "SIN"), ("BOM", "MAA"), ("BOM", "DXB"),
    ("MAA", "SIN"), ("MAA", "DXB"),
    ("SYD", "HKG"),
    ("BLR", "DEL"),
    ("BLR", "BOM"),
    ("BLR", "HYD"),

    ("DEL", "CCU"),
    ("DEL", "HYD"),

    ("BOM", "MAA"),
    ("BOM", "CCU"),

    ("HYD", "MAA"),
    ("HYD", "CCU"),

    ("CCU", "DEL"),
    ("MAA", "BLR")
]

RUNWAYS = [
    {"id": "RWY-09", "status": "Open", "usage": "Departures"},
    {"id": "RWY-27", "status": "Open", "usage": "Arrivals"},
    {"id": "RWY-18", "status": "Maintenance", "usage": "Closed"},
]

def get_flights():
    return list(
        db.flights.find({}, {"_id": 0})
    )

def to_jsonable(value):
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items() if k != "_id"}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value

def serialize_doc(doc):
    if not doc:
        return None
    data = dict(doc)
    data["_id"] = str(data["_id"])
    return to_jsonable(data)

def now():
    return datetime.utcnow()

def init_db():
    # Create helpful indexes
    flights_col.create_index([("flight_no", DESCENDING)], unique=True)
    weather_col.create_index([("airport_code", DESCENDING), ("updated_at", DESCENDING)])
    runways_col.create_index([("airport_code", DESCENDING), ("runway_no", DESCENDING)], unique=True)
    logs_col.create_index([("created_at", DESCENDING)])

def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

def build_route_graph(weather_map):
    graph = {code: {} for code in AIRPORTS}

    for a, b in ROUTES:
        if a not in AIRPORTS or b not in AIRPORTS:
            continue

        wa = weather_map.get(a, {})
        wb = weather_map.get(b, {})
        risk_a = wa.get("risk", "green")
        risk_b = wb.get("risk", "green")

        if risk_a == "red" and risk_b == "red":
            continue

        dist = haversine(
            AIRPORTS[a]["lat"], AIRPORTS[a]["lon"],
            AIRPORTS[b]["lat"], AIRPORTS[b]["lon"]
        )

        penalty = 1.0
        if "yellow" in (risk_a, risk_b):
            penalty = 1.35
        if "red" in (risk_a, risk_b):
            penalty = 2.5

        graph[a][b] = dist * penalty
        graph[b][a] = dist * penalty

    return graph


def dijkstra(graph, start, end):
    dist = {node: float("inf") for node in graph}
    prev = {node: None for node in graph}
    dist[start] = 0.0
    visited = set()

    while True:
        current = None
        current_dist = float("inf")

        for node in graph:
            if node not in visited and dist[node] < current_dist:
                current = node
                current_dist = dist[node]

        if current is None:
            break

        if current == end:
            break

        visited.add(current)

        for neighbor, weight in graph[current].items():
            alt = dist[current] + weight
            if alt < dist[neighbor]:
                dist[neighbor] = alt
                prev[neighbor] = current

    if dist[end] == float("inf"):
        return None

    path = []
    node = end
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path

def deterministic_weather(code):
    random.seed(sum(ord(c) for c in code) + datetime.utcnow().hour)
    temp = round(random.uniform(10, 38), 1)
    wind = round(random.uniform(4, 48), 1)
    chance = random.random()

    if wind > 35 or chance > 0.82:
        risk = "red"
    elif wind > 20 or chance > 0.55:
        risk = "yellow"
    else:
        risk = "green"

    return {
        "temperature": temp,
        "wind": wind,
        "risk": risk,
        "label": "Severe" if risk == "red" else "Moderate" if risk == "yellow" else "Safe"
    }

def ai_delay_prediction(flight, origin_weather, destination_weather):
    score = 0

    if origin_weather["risk"] == "red":
        score += 45
    elif origin_weather["risk"] == "yellow":
        score += 20

    if destination_weather["risk"] == "red":
        score += 35
    elif destination_weather["risk"] == "yellow":
        score += 15

    if origin_weather["wind"] > 30 or destination_weather["wind"] > 30:
        score += 15

    departure = flight.get("departure", "12:00")
    arrival = flight.get("arrival", "12:00")

    if departure < "10:00" or arrival > "22:00":
        score += 8

    if score >= 60:
        return "High Delay Risk"
    if score >= 30:
        return "Moderate Delay Risk"
    return "Low Delay Risk"

def get_flights():
    docs = list(flights_col.find().sort("updated_at", DESCENDING))
    if docs:
        return [serialize_doc(d) for d in docs]
    return FLIGHTS

def get_weather_updates():
    docs = list(weather_col.find().sort("updated_at", DESCENDING))
    return [serialize_doc(d) for d in docs]

def get_runways():
    docs = list(runways_col.find().sort("updated_at", DESCENDING))
    if docs:
        return [serialize_doc(d) for d in docs]
    return RUNWAYS

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/history")
def history():
    return render_template("history.html")

@app.route("/api/dashboard2")
def dashboard2():
    weather_map = {code: deterministic_weather(code) for code in AIRPORTS}
    flights = get_flights()
    runways = get_runways()
    delay_minutes = get_delay(
    flight["flight_no"]
    )

    live_flights = []
    for flight in flights:
        origin = flight["origin"]
        destination = flight["destination"]

        origin_weather = weather_map.get(origin, {"risk": "green", "label": "Safe", "wind": 0})
        destination_weather = weather_map.get(destination, {"risk": "green", "label": "Safe", "wind": 0})
        delay = ai_delay_prediction(flight, origin_weather, destination_weather)

        live_flights.append({
            **flight,
            "origin_name": AIRPORTS.get(origin, {}).get("name", origin),
            "destination_name": AIRPORTS.get(destination, {}).get("name", destination),
            "origin_weather": weather.get("label", "Unknown"),
            "destination_weather": destination_weather,
            "delay_prediction": delay
        })


    return jsonify({
        "airports": AIRPORTS,
        "weather": weather_map,
        "flights": live_flights,
        "runways": runways,
        "delay_minutes": delay_minutes
    })

@app.route("/api/optimize/<flight_no>")
def optimize(flight_no):
    weather_docs = list(db.weather.find({}, {"_id": 0}))

    weather_map = {}

    for w in weather_docs:

        weather_map[w["airport"]] = {
            "label": w["label"],
            "risk": (
                "green" if w["label"] == "Safe"
                else "yellow" if w["label"] == "Moderate"
                else "red"
            ),
            "wind": float(w.get("wind", 0))
        }
    flights = get_flights()
    print("FLIGHTS DATA:")
    print(flights)
    print(type(flights))

    if len(flights) > 0:
        print(type(flights[0]))
        print(flights[0])
    selected = next((f for f in flights if f["flight_no"] == flight_no), None)

    if not selected:
        return jsonify({"error": "Flight not found"}), 404
    print(type(AIRPORTS))
    print(AIRPORTS)

    graph = build_route_graph(weather_map)
    print("Flight:", selected["origin"], "->", selected["destination"])
    print("BLR Connections:", graph.get("BLR"))
    print("DEL Connections:", graph.get("DEL"))
    path = dijkstra(graph, selected["origin"], selected["destination"])

    if not path:
        return jsonify({"error": "No safe route available because of weather"}), 400

    total_km = 0.0
    for i in range(len(path) - 1):
        a = path[i]
        b = path[i + 1]
        total_km += haversine(
            AIRPORTS[a]["lat"], AIRPORTS[a]["lon"],
            AIRPORTS[b]["lat"], AIRPORTS[b]["lon"]
        )

    origin_weather = weather_map[selected["origin"]]
    destination_weather = weather_map[selected["destination"]]
    delay = ai_delay_prediction(selected, origin_weather, destination_weather)

    log_doc = {
        "created_at": now(),
        "flight_no": selected["flight_no"],
        "origin": selected["origin"],
        "destination": selected["destination"],
        "route": " -> ".join(path),
        "total_km": round(total_km, 2),
        "weather_status": f"{origin_weather['label']} / {destination_weather['label']}",
        "delay_prediction": delay
    }
    logs_col.insert_one(log_doc)
    fuel_used = round(total_km *2.8, 2)

    fuel_saved = round(fuel_used * 0.12, 2)
    co2_reduction = round(
        fuel_saved * 2.5,
        2
    )
    diversion = None

    if origin_weather["label"] == "Severe":
        diversion = nearest_safe_airport(
            selected["origin"]
        )
    return jsonify({
        "flight_no": selected["flight_no"],
        "origin": selected["origin"],
        "destination": selected["destination"],
        "path": path,
        "path_coords": [
            {
                "code": code,
                "name": code,
                "lat": AIRPORTS[code]["lat"],
                "lon": AIRPORTS[code]["lon"]
            }
            for code in path
        ],
        "total_km": round(total_km, 2),
        "fuel_used": fuel_used,
        "fuel_saved": fuel_saved,
        "delay_prediction": delay,
        "co2_reduction": co2_reduction,
        "diversion_airport": diversion,
        "weather": {
            selected["origin"]: origin_weather,
            selected["destination"]: destination_weather
        }
    })
@app.route("/api/flight/<flight_no>/status", methods=["POST"])
def update_flight_status(flight_no):

    data = request.json

    update_doc = {
        "status": data.get("status")
    }

    if data.get("status") == "Delayed":

        update_doc["delay_minutes"] = int(
            data.get("delay_minutes", 15)
        )

        update_doc["delay_reason"] = data.get(
            "delay_reason",
            "Weather"
        )

    flights_col.update_one(
        {"flight_no": flight_no},
        {"$set": update_doc}
    )

    return jsonify({"success": True})

@app.route("/api/logs")
def logs():
    rows = list(logs_col.find().sort("created_at", DESCENDING).limit(20))
    return jsonify([serialize_doc(row) for row in rows])

@app.route("/api/admin/flight/upsert", methods=["POST"])
def admin_upsert_flight():
    data = request.get_json(force=True)

    flight_no = data["flight_no"]
    origin = data["origin"]
    destination = data["destination"]
    departure_time = data["departure_time"]
    arrival_time = data["arrival_time"]
    status = data.get("status", "Scheduled")
    gate = data.get("gate")
    runway = data.get("runway")

    doc = {
        "flight_no": flight_no,
        "origin": origin,
        "destination": destination,
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "status": status,
        "gate": gate,
        "runway": runway,
        "updated_at": now()
    }

    flights_col.update_one(
        {"flight_no": flight_no},
        {"$set": doc, "$setOnInsert": {"created_at": now()}},
        upsert=True
    )

    logs_col.insert_one({
        "created_at": now(),
        "flight_no": flight_no,
        "origin": origin,
        "destination": destination,
        "route": "manual/admin update",
        "total_km": 0,
        "weather_status": "N/A",
        "delay_prediction": "N/A"
    })

    return jsonify({"message": "Flight saved successfully"})

@app.route("/api/admin/weather/upsert", methods=["POST"])
def admin_upsert_weather():
    data = request.get_json(force=True)

    airport_code = data["airport_code"]
    temperature = data["temperature"]
    windspeed = data["windspeed"]
    weathercode = data["weathercode"]
    risk_level = data["risk_level"]
    description = data["description"]

    doc = {
        "airport_code": airport_code,
        "temperature": temperature,
        "windspeed": windspeed,
        "weathercode": weathercode,
        "risk_level": risk_level,
        "description": description,
        "source": "backend",
        "updated_at": now()
    }

    weather_col.insert_one(doc)

    return jsonify({"message": "Weather updated successfully"})

@app.route("/api/admin/runway/upsert", methods=["POST"])
def admin_upsert_runway():
    data = request.get_json(force=True)

    airport_code = data["airport_code"]
    runway_no = data["runway_no"]
    status = data["status"]
    remarks = data.get("remarks")

    doc = {
        "airport_code": airport_code,
        "runway_no": runway_no,
        "status": status,
        "remarks": remarks,
        "updated_at": now()
    }

    runways_col.update_one(
        {"airport_code": airport_code, "runway_no": runway_no},
        {"$set": doc, "$setOnInsert": {"created_at": now()}},
        upsert=True
    )

    return jsonify({"message": "Runway updated successfully"})

@app.route("/api/flights")
def api_flights():
    rows = get_flights()
    return jsonify(rows)

@app.route("/api/weather")
def api_weather():
    rows = get_weather_updates()
    return jsonify(rows)

@app.route("/api/runways")
def api_runways():
    rows = get_runways()
    return jsonify(rows)

@app.route("/api/stats")
def stats():

    total_flights = len(get_flights())
    total_logs = logs_col.count_documents({})
    total_weather = weather_col.count_documents({})
    total_runways = runways_col.count_documents({})

    return jsonify({
        "total_flights": total_flights,
        "flight_history": total_logs,
        "weather_updates": total_weather,
        "runways": total_runways
    })
@app.route("/api/weather-heatmap")
def weather_heatmap():
    heatmap_data = []

    for code, airport in AIRPORTS.items():
        weather_doc = db.weather.find_one(
            {"airport": code},
            {"_id": 0}
        )
        risk, label = weather_risk(weather_doc)

        weather_doc["risk"] = risk
        weather_doc["label"] = label

        heatmap_data.append({
            "code": code,
            "name": airport["name"],
            "lat": airport["lat"],
            "lon": airport["lon"],
            "temperature": weather_doc["temperature"],
            "humidity": weather_doc["humidity"],
            "precipitation": weather_doc["precipitation"],
            "wind": weather_doc["wind"],
            "gusts": weather_doc["gusts"],
            "risk": weather_doc["risk"],
            "label": weather_doc["label"]
        })

    return jsonify(heatmap_data)
import requests

def fetch_real_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "auto"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()["current"]

    return {
        "temperature": data["temperature_2m"],
        "humidity": data["relative_humidity_2m"],
        "precipitation": data["precipitation"],
        "wind": data["wind_speed_10m"],
        "gusts": data["wind_gusts_10m"],
        "weather_code": data["weather_code"]
    }
def weather_risk(weather):
    code = weather["weather_code"]
    wind = weather["wind"]

    if wind >= 35 or code in [65, 66, 67, 75, 82]:
        return "red", "Severe"
    elif wind >= 20 or code in [45, 48, 51, 53, 55, 61, 63, 71, 73, 75, 80, 81]:
        return "yellow", "Moderate"
    return "green", "Safe"
def get_delay(flight_no):

    delay = db.flight_delays.find_one(
        {"flight_no": flight_no},
        {"_id": 0}
    )

    if delay:
        return delay["delay_minutes"]

    return 0
@app.route("/api/update_status/<flight_no>/<status>", methods=["POST"])
def update_status(flight_no, status):

    db.flights.update_one(
        {"flight_no": flight_no},
        {"$set": {"status": status}}
    )

    return jsonify({
        "message": "Status updated",
        "flight_no": flight_no,
        "status": status
    })
@app.route("/test")
def test():
    return jsonify({
        "flights": list(db.flights.find({}, {"_id": 0}))
    })
@app.route("/dashboard_test")
def dashboard_test():

    return jsonify({
        "flights": list(db.flights.find({}, {"_id": 0})),
        "runways": list(db.runways.find({}, {"_id": 0})),
        "logs": list(db.flight_logs.find({}, {"_id": 0}))
    })
def calculate_delay(label):

    if label == "Safe":
        return 0

    elif label == "Moderate":
        return 20

    elif label == "Severe":
        return 60

    return 15
def calculate_risk_score(weather_label, delay):

    score = 0

    if weather_label == "Moderate":
        score += 30

    elif weather_label == "Severe":
        score += 60

    score += min(delay, 40)

    return min(score, 100)
@app.route("/api/congestion")
def congestion():

    flights = list(db.flights.find({}, {"_id": 0}))

    airports = {}

    for flight in flights:

        airports.setdefault(flight["origin"], 0)
        airports[flight["origin"]] += 1

    result = []

    for airport, count in airports.items():

        congestion = min(100, count * 10)

        result.append({
            "airport": airport,
            "congestion": congestion
        })

    return jsonify(result)
@app.route("/api/analytics")
def analytics():

    flights = list(db.flights.find({}, {"_id": 0}))

    total = len(flights)

    delayed = 0
    cancelled = 0

    total_delay = 0

    airport_count = {}

    for flight in flights:

        airport_count[flight["origin"]] = \
            airport_count.get(flight["origin"], 0) + 1

        status = flight.get("status", "")

        if status == "Delayed":
            delayed += 1

        if status == "Cancelled":
            cancelled += 1

        delay = int(
            str(flight.get("delay_prediction", "0"))
            .replace(" min", "")
        )

        total_delay += delay

    busiest = max(
        airport_count,
        key=airport_count.get
    )

    return jsonify({
        "total_flights": total,
        "delayed_flights": delayed,
        "cancelled_flights": cancelled,
        "average_delay":
            round(total_delay / max(total, 1), 2),
        "busiest_airport": busiest
    })
def nearest_safe_airport(origin):

    best = None
    best_dist = 999999

    for code in AIRPORTS:

        if code == origin:
            continue

        weather = deterministic_weather(code)

        if weather["label"] != "Safe":
            continue

        dist = haversine(
            AIRPORTS[origin]["lat"],
            AIRPORTS[origin]["lon"],
            AIRPORTS[code]["lat"],
            AIRPORTS[code]["lon"]
        )

        if dist < best_dist:
            best_dist = dist
            best = code

    return best


if __name__ == "__main__":
    init_db()
    app.run(debug=True)