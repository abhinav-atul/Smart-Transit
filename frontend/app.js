// 1. Initialize Map
const map = L.map('map').setView([28.7041, 77.1025], 14); // Default to Delhi

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Bus Icon
const busIcon = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/3448/3448339.png',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20]
});

// Store marker reference
let busMarker = null;

// 2. Fetch Data Function
async function fetchBusData() {
    try {
        const response = await fetch('http://localhost:8000/api/v1/status');
        const data = await response.json();
        
        // We are focusing on "BUS-101" for this demo
        const bus = data["BUS-101"];
        
        if (bus) {
            updateMap(bus);
            updateSidebar(bus);
        }
    } catch (error) {
        console.error("Error fetching bus data:", error);
    }
}

// 3. Update Map Marker
function updateMap(bus) {
    const { lat, lng } = bus.location;
    
    if (busMarker) {
        // Smoothly move marker
        busMarker.setLatLng([lat, lng]);
    } else {
        // Create marker if it doesn't exist
        busMarker = L.marker([lat, lng], { icon: busIcon }).addTo(map);
        busMarker.bindPopup("<b>BUS-101</b><br>Click for details").openPopup();
        
        // Center map on first load
        map.panTo([lat, lng]);
        
        // Add click event
        busMarker.on('click', () => {
            document.getElementById('bus-info').classList.remove('hidden');
            document.getElementById('placeholder').style.display = 'none';
        });
    }
}

// 4. Update Sidebar UI
function updateSidebar(bus) {
    document.getElementById('bus-id').innerText = "BUS-101";
    document.getElementById('route-name').innerText = bus.route;
    
    // ETA Section
    if (bus.eta) {
        document.getElementById('next-stop').innerText = bus.eta.next_stop || "Unknown";
        document.getElementById('eta-time').innerText = bus.eta.minutes + " min";
        document.getElementById('eta-status').innerText = bus.eta.status;
        
        // Color code status
        const statusElem = document.getElementById('eta-status');
        statusElem.style.color = bus.eta.status.includes("Delayed") ? "#dc2626" : "#16a34a";
    }

    // Crowd Section
    if (bus.crowd) {
        const badge = document.getElementById('crowd-level');
        const level = bus.crowd.level;
        
        badge.innerText = level;
        document.getElementById('crowd-count').innerText = `${bus.crowd.count} passengers detected`;

        // Reset classes
        badge.className = 'badge';
        if (level.includes("GREEN")) badge.classList.add('bg-green');
        else if (level.includes("ORANGE")) badge.classList.add('bg-orange');
        else if (level.includes("RED")) badge.classList.add('bg-red');
    }
}

// 5. Poll every 1 second
setInterval(fetchBusData, 1000);
fetchBusData(); // Initial call