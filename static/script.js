let map;

function updateClock() {
    const clock = document.getElementById("clock");
    if (!clock) return;
    clock.innerText = new Date().toLocaleTimeString();
}

function riskColor(risk) {
    if (risk === "red") return "red";
    if (risk === "yellow") return "orange";
    return "green";
}

function safeText(value) {
    return value === undefined || value === null ? "" : value;
}

function initMap() {
    const mapElement = document.getElementById("map");
    if (!mapElement) return;

    map = L.map("map").setView([20, 78], 3);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    setTimeout(() => map.invalidateSize(), 200);
}

async function loadDashboard() {
    try {
        const response = await fetch("/api/dashboard");
        const data = await response.json();

        const liveFlights = document.getElementById("liveFlights");
        const runways = document.getElementById("runways");

        if (liveFlights) {
            liveFlights.innerHTML = "";

            data.flights.forEach(flight => {
                const card = document.createElement("div");
                card.className = "item-card";
                card.innerHTML = `
    <div class="item-title">${safeText(flight.flight_no)}</div>
    <div>${safeText(flight.origin)} → (${safeText(flight.destination)})</div>
    <div>Departure: ${safeText(flight.departure)}</div>
    <div>Arrival: ${safeText(flight.arrival)}</div>

    <div>Status: ${safeText(flight.status || "Scheduled")}</div>

    <div>Delay: ${safeText(flight.status === "Cancelled"
    ? "N/A"
    : flight.delay_prediction)}<br>
    Reason: ${flight.delay_reason || "Weather"}</div>
    <div>Origin Weather: ${safeText(flight.origin_weather?.label)}
    <p>Origin Weather: ${flight.origin_weather}</p>
    </div>

    <button onclick="updateStatus('${flight.flight_no}','Boarding')">
        Boarding
    </button>

    <button onclick="updateStatus('${flight.flight_no}','Departed')">
        Departed
    </button>

    <button onclick="updateStatus('${flight.flight_no}','Delayed')">
        Delayed
    </button>

    <button onclick="updateStatus('${flight.flight_no}','Cancelled')">
        Cancelled
    </button>
   
    ${
flight.status === "Cancelled"
?
`<button disabled
style="background:gray">
Cancelled
</button>`
:
`<button class="opt-btn"
data-flight="${safeText(flight.flight_no)}">
Optimize
</button>`
}
`;
                liveFlights.appendChild(card);
            });

            liveFlights.querySelectorAll(".opt-btn").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const flightNo = btn.dataset.flight;
                    try {
                        const res = await fetch(`/api/optimize/${flightNo}`);
                        const result = await res.json();
                       



                        if (!res.ok) {
                            alert(result.error || "Could not optimize route");
                            return;
                        }

                        const coords = result.path_coords.map(p => [p.lat, p.lon]);
                        let smoothCoords = [];

                        for (let i = 0; i < coords.length - 1; i++) {
                            const start = coords[i];
                            const end = coords[i + 1];

                            for (let j = 0; j <= 50; j++) {
                                const lat = start[0] + (end[0] - start[0]) * (j / 50);
                                const lon = start[1] + (end[1] - start[1]) * (j / 50);

                                smoothCoords.push([lat, lon]);
                            }
                        }
                        if (window.currentRouteLine) {
                            map.removeLayer(window.currentRouteLine);
                        }

                        window.currentRouteLine = L.polyline(smoothCoords, {
                            color: "cyan",
                            weight: 4
                        }).addTo(map);
                        // Remove old airplane marker
                        if (window.airplaneMarker) {
                           map.removeLayer(window.airplaneMarker);
                        }

                        // Create airplane marker at starting point
                       const planeIcon = L.divIcon({
                           html: "✈️",
                           className: "plane-icon",
                           iconSize: [30, 30]
                       });

                       window.airplaneMarker = L.marker(smoothCoords[0], {

                           icon: planeIcon
                       }).addTo(map);
                        // Animate airplane movement
                        let step = 0;

                        if (window.flightAnimation) {
                            clearInterval(window.flightAnimation);
                        }

                        window.flightAnimation = setInterval(() => {
                            step++;

                            if (step >= smoothCoords.length) {
                                clearInterval(window.flightAnimation);
                                return;
                            }

                            window.airplaneMarker.setLatLng(smoothCoords[step]);
                        }, 100);

                        map.fitBounds(window.currentRouteLine.getBounds(),
                                      {
                                          padding:[50,50]
                                      }
                        
                        );
                        document.getElementById("route-result").innerHTML = `
                        <h3>Optimization Report</h3>

                        <p><b>Flight:</b> ${flightNo}</p>

                        <p><b>Distance:</b> ${result.total_km} km</p>

                        <p><b>Fuel Usage:</b> ${result.fuel_used} L</p>

                        <p><b>Fuel Saved:</b> ${result.fuel_saved} L</p>

                        <p><b>Delay Risk:</b> ${result.delay_prediction}</p>
                        `;

                       alert(
                       `ROUTE OPTIMIZATION REPORT

                       Flight: ${flightNo}

                       Distance: ${result.total_km} km

                       Estimated Fuel Usage: ${result.fuel_used} L

                       Fuel Saved: ${result.fuel_saved} L

                       Delay Risk: ${result.delay_prediction}`
                       );
                        loadLogs();
                    } catch (err) {
                        console.error(err);
                        alert("Error:"+ err.message);
                    }
                });
            });
        }

        if (runways) {
            runways.innerHTML = "";
            data.runways.forEach(r => {
                const card = document.createElement("div");
                card.className = "item-card";
                card.innerHTML = `
                    <div class="item-title">${safeText(r.id || r.runway_no)}</div>
                    <div>Status: ${safeText(r.status)}</div>
                    <div>Usage: ${safeText(r.usage || "")}</div>
                    <div>${safeText(r.remarks || "")}</div>
                `;
                runways.appendChild(card);
            });
        }

        if (map) {
            if (window.airportLayer) {
                window.airportLayer.remove();
            }
            window.airportLayer = L.layerGroup().addTo(map);

            Object.entries(data.airports).forEach(([code, airport]) => {
                const weather = data.weather[code];
                const color = riskColor(weather?.risk);

                L.circleMarker([airport.lat, airport.lon], {
                    radius: 10,
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.8,
                    weight: 2
                }).addTo(window.airportLayer).bindPopup(`
                    <b>${code} - ${airport.name}</b><br>
                    Temperature: ${weather?.temperature}°C<br>
                    Wind: ${weather?.wind} km/h<br>
                    Risk: ${weather?.label}
                `);
            });
        }
    } catch (error) {
        console.error("Dashboard load error:", error);
    }
}

async function loadLogs() {
    try {
        const response = await fetch("/api/logs");
        const data = await response.json();

        const logs = document.getElementById("flightLogs");
        if (!logs) return;

        if (!data.length) {
            logs.innerHTML = `<div class="empty">No flight logs yet.</div>`;
            return;
        }

        logs.innerHTML = data.map(log => `
            <div class="item-card">
                <div class="item-title">${safeText(log.flight_no)}</div>
                <div>${safeText(log.origin)} → ${safeText(log.destination)}</div>
                <div>Route: ${safeText(log.route)}</div>
                <div>${safeText(log.total_km)} km</div>
                <div>${safeText(log.weather_status)}</div>
                <div>${safeText(log.delay_prediction)}</div>
                <div class="log-time">${safeText(log.created_at)}</div>
            </div>
        `).join("");
    } catch (error) {
        console.error("Logs load error:", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    updateClock();
    setInterval(updateClock, 1000);

    initMap();
    loadDashboard();
    loadLogs();

    setInterval(() => {
        loadDashboard();
        loadLogs();
    }, 30000);
});
async function updateStatus(flightNo, status){

    let payload = {
        status: status
    };

    if(status === "Delayed"){

        const mins = prompt(
            "Enter delay duration (minutes):",
            "15"
        );

        if(mins === null) return;

        const reason = prompt(
            "Delay Reason?\nWeather\nTechnical\nAir Traffic\nCrew",
            "Weather"
        );

        payload.delay_minutes = parseInt(mins);
        payload.delay_reason = reason;
    }

    await fetch(`/api/flight/${flightNo}/status`,{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify(payload)
    });

    loadDashboard();
}