def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS airports (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_no TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled',
            gate TEXT,
            runway TEXT,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_code TEXT NOT NULL,
            temperature REAL NOT NULL,
            windspeed REAL NOT NULL,
            weathercode INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            description TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'backend',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (airport_code) REFERENCES airports(code)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS runways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_code TEXT NOT NULL,
            runway_no TEXT NOT NULL,
            status TEXT NOT NULL,
            remarks TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (airport_code) REFERENCES airports(code)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS flight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            flight_no TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            route TEXT NOT NULL,
            total_km REAL NOT NULL,
            weather_status TEXT NOT NULL,
            delay_prediction TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS route_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_no TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()