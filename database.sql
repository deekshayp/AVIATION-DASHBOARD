-- =========================================================
-- DATABASE: Flight Path Optimization System
-- =========================================================

CREATE DATABASE IF NOT EXISTS flight_optimization;
USE flight_optimization;

-- =========================================================
-- 1. USERS TABLE
-- Stores login details for admin/user
-- =========================================================
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 2. AIRCRAFT TABLE
-- Stores aircraft details for fuel calculation
-- =========================================================
CREATE TABLE IF NOT EXISTS aircraft (
    aircraft_id INT AUTO_INCREMENT PRIMARY KEY,
    aircraft_name VARCHAR(100) NOT NULL,
    aircraft_type VARCHAR(100),
    fuel_rate_per_km DECIMAL(10,2) NOT NULL,
    max_speed_kmph DECIMAL(10,2),
    max_range_km DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 3. FLIGHTS TABLE
-- Main flight history table
-- =========================================================
CREATE TABLE IF NOT EXISTS flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    aircraft_id INT,
    flight_code VARCHAR(50) NOT NULL,
    source_airport VARCHAR(100) NOT NULL,
    destination_airport VARCHAR(100) NOT NULL,
    departure_time DATETIME,
    arrival_time DATETIME,
    total_distance_km DECIMAL(10,2),
    total_fuel_estimate DECIMAL(10,2),
    route_status VARCHAR(50) DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- =========================================================
-- 4. WEATHER DATA TABLE
-- Stores weather details related to each flight
-- =========================================================
CREATE TABLE IF NOT EXISTS weather_data (
    weather_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT,
    location VARCHAR(100) NOT NULL,
    weather_condition VARCHAR(100),
    temperature DECIMAL(5,2),
    wind_speed DECIMAL(5,2),
    visibility DECIMAL(5,2),
    humidity DECIMAL(5,2),
    pressure DECIMAL(7,2),
    weather_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =========================================================
-- 5. ROUTE HISTORY TABLE
-- Stores original and optimized routes
-- =========================================================
CREATE TABLE IF NOT EXISTS route_history (
    route_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT,
    route_type VARCHAR(50) NOT NULL,   -- original / optimized / emergency
    source_node VARCHAR(100) NOT NULL,
    destination_node VARCHAR(100) NOT NULL,
    route_distance_km DECIMAL(10,2),
    route_fuel_estimate DECIMAL(10,2),
    is_optimal BOOLEAN DEFAULT FALSE,
    rerouted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =========================================================
-- 6. ROUTE COORDINATES TABLE
-- Stores latitude/longitude points for map drawing
-- =========================================================
CREATE TABLE IF NOT EXISTS route_coordinates (
    coord_id INT AUTO_INCREMENT PRIMARY KEY,
    route_id INT,
    latitude DECIMAL(10,6) NOT NULL,
    longitude DECIMAL(10,6) NOT NULL,
    point_order INT NOT NULL,
    FOREIGN KEY (route_id) REFERENCES route_history(route_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =========================================================
-- 7. ALERTS TABLE
-- Stores warnings like bad weather, rerouting, fuel alerts
-- =========================================================
CREATE TABLE IF NOT EXISTS alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT,
    alert_type VARCHAR(50) NOT NULL,
    alert_message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =========================================================
-- 8. FLIGHT DASHBOARD TABLE
-- Stores live status for quick display in dashboard
-- =========================================================
CREATE TABLE IF NOT EXISTS flight_dashboard (
    dashboard_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT,
    current_status VARCHAR(50) DEFAULT 'scheduled',
    current_latitude DECIMAL(10,6),
    current_longitude DECIMAL(10,6),
    remaining_distance_km DECIMAL(10,2),
    remaining_fuel DECIMAL(10,2),
    eta DATETIME,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =========================================================
-- 9. AIRPORTS TABLE
-- Optional: stores airport information
-- =========================================================
CREATE TABLE IF NOT EXISTS airports (
    airport_id INT AUTO_INCREMENT PRIMARY KEY,
    airport_code VARCHAR(10) NOT NULL UNIQUE,
    airport_name VARCHAR(150) NOT NULL,
    city VARCHAR(100),
    country VARCHAR(100),
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 10. FLIGHT LOGS TABLE
-- Stores detailed activity logs
-- =========================================================
CREATE TABLE IF NOT EXISTS flight_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT,
    log_type VARCHAR(50),
    log_message TEXT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =========================================================
-- SAMPLE DATA INSERTS
-- =========================================================

INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@example.com', 'admin123', 'admin');

INSERT INTO aircraft (aircraft_name, aircraft_type, fuel_rate_per_km, max_speed_kmph, max_range_km)
VALUES ('Airbus A320', 'Passenger', 2.50, 830, 6150);

INSERT INTO airports (airport_code, airport_name, city, country, latitude, longitude)
VALUES 
('BLR', 'Kempegowda International Airport', 'Bangalore', 'India', 13.1989, 77.7066),
('DEL', 'Indira Gandhi International Airport', 'Delhi', 'India', 28.5562, 77.1000);

INSERT INTO flights (
    user_id, aircraft_id, flight_code,
    source_airport, destination_airport,
    departure_time, arrival_time,
    total_distance_km, total_fuel_estimate, route_status
)
VALUES (
    1, 1, 'FL123',
    'Bangalore', 'Delhi',
    '2026-06-03 10:00:00',
    '2026-06-03 12:30:00',
    1700.00, 4250.00, 'planned'
);

INSERT INTO weather_data (
    flight_id, location, weather_condition,
    temperature, wind_speed, visibility, humidity, pressure
)
VALUES (
    1, 'Bangalore', 'Cloudy',
    28.50, 12.40, 8.00, 70.00, 1012.30
);

INSERT INTO route_history (
    flight_id, route_type, source_node, destination_node,
    route_distance_km, route_fuel_estimate, is_optimal, rerouted
)
VALUES (
    1, 'optimized', 'Bangalore', 'Delhi',
    1685.00, 4200.00, TRUE, FALSE
);

INSERT INTO route_coordinates (route_id, latitude, longitude, point_order)
VALUES
(1, 13.198900, 77.706600, 1),
(1, 15.000000, 78.500000, 2),
(1, 18.000000, 79.500000, 3),
(1, 21.000000, 80.500000, 4),
(1, 24.000000, 81.500000, 5),
(1, 28.556200, 77.100000, 6);

INSERT INTO alerts (flight_id, alert_type, alert_message, severity)
VALUES (1, 'weather', 'Cloudy weather detected on route. Monitoring required.', 'low');

INSERT INTO flight_dashboard (
    flight_id, current_status, current_latitude, current_longitude,
    remaining_distance_km, remaining_fuel, eta
)
VALUES (
    1, 'in progress', 18.000000, 79.500000,
    900.00, 2400.00, '2026-06-03 12:30:00'
);

INSERT INTO flight_logs (flight_id, log_type, log_message)
VALUES
(1, 'created', 'Flight created successfully'),
(1, 'weather_update', 'Weather data updated'),
(1, 'route_optimized', 'Best route selected based on weather and fuel');

-- =========================================================
-- END OF SCRIPT
-- =========================================================