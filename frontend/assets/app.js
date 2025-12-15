// --- CONFIGURATION ---
// The URL of your Python/FastAPI Backend
const API_BASE_URL = "http://localhost:8000";
const GOOGLE_MAPS_API_KEY = "AIzaSyDec5RO1JPrJdX0X5ntqupEU8RQ8rxDiwM"; // Replace if needed

// --- GOOGLE MAPS STYLES ---
const lightMapStyle = [{ elementType: "geometry", stylers: [{ color: "#f5f5f5" }] }, { elementType: "labels.icon", stylers: [{ visibility: "off" }] }, { elementType: "labels.text.fill", stylers: [{ color: "#616161" }] }, { elementType: "labels.text.stroke", stylers: [{ color: "#f5f5f5" }] }, { featureType: "administrative.land_parcel", elementType: "labels.text.fill", stylers: [{ color: "#bdbdbd" }] }, { featureType: "poi", elementType: "geometry", stylers: [{ color: "#eeeeee" }] }, { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#757575" }] }, { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#e5e5e5" }] }, { featureType: "poi.park", elementType: "labels.text.fill", stylers: [{ color: "#9e9e9e" }] }, { featureType: "road", elementType: "geometry", stylers: [{ color: "#ffffff" }] }, { featureType: "road.arterial", elementType: "labels.text.fill", stylers: [{ color: "#757575" }] }, { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#dadada" }] }, { featureType: "road.highway", elementType: "labels.text.fill", stylers: [{ color: "#616161" }] }, { featureType: "road.local", elementType: "labels.text.fill", stylers: [{ color: "#9e9e9e" }] }, { featureType: "transit.line", elementType: "geometry", stylers: [{ color: "#e5e5e5" }] }, { featureType: "transit.station", elementType: "geometry", stylers: [{ color: "#eeeeee" }] }, { featureType: "water", elementType: "geometry", stylers: [{ color: "#c9c9c9" }] }, { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#9e9e9e" }] }];
const darkMapStyle = [{ elementType: "geometry", stylers: [{ color: "#242f3e" }] }, { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] }, { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] }, { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] }, { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] }, { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#263c3f" }] }, { featureType: "poi.park", elementType: "labels.text.fill", stylers: [{ color: "#6b9a76" }] }, { featureType: "road", elementType: "geometry", stylers: [{ color: "#38414e" }] }, { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#212a37" }] }, { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#9ca5b3" }] }, { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#746855" }] }, { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#1f2835" }] }, { featureType: "road.highway", elementType: "labels.text.fill", stylers: [{ color: "#f3d19c" }] }, { featureType: "transit", elementType: "geometry", stylers: [{ color: "#2f3948" }] }, { featureType: "transit.station", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] }, { featureType: "water", elementType: "geometry", stylers: [{ color: "#17263c" }] }, { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#515c6d" }] }, { featureType: "water", elementType: "labels.text.stroke", stylers: [{ color: "#17263c" }] }];

// --- APP GLOBALS ---
let map, infoWindow;
let busMarkers = {};     // Object to store Google Maps Markers by Bus ID
let routePolylines = {}; // Object to store Polylines by Route ID
let stopMarkers = [];    // Array of stop markers for the selected route
let selectedRouteId = null;

// Data Stores
let allRoutesData = {};   // { "AS-1": { routeName: "...", stops: [...] }, ... }
let allAvailableStops = []; // Array of { name, lat, lng }
let stopToRoutesMap = new Map(); // Map<StopName, [RouteID]>

// --- DOM ELEMENTS ---
const finderViewBtn = document.getElementById('finder-view-btn');
const commuterViewBtn = document.getElementById('commuter-view-btn');
const authorityViewBtn = document.getElementById('authority-view-btn');
const finderView = document.getElementById('finder-view');
const commuterView = document.getElementById('commuter-view');
const authorityView = document.getElementById('authority-view');
const findBusesBtn = document.getElementById('find-buses-btn');
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const togglePanelBtn = document.getElementById('toggle-panel-btn');
const panelContent = document.getElementById('panel-content');
const sosBtn = document.getElementById('sos-btn');
const sosModal = document.getElementById('sos-modal');
const closeSosModalBtn = document.getElementById('close-sos-modal-btn');
const finderResultsList = document.getElementById('finder-results-list');

// --- EVENT LISTENERS ---
finderViewBtn.addEventListener('click', () => switchView('finder'));
commuterViewBtn.addEventListener('click', () => switchView('commuter'));
authorityViewBtn.addEventListener('click', () => switchView('authority'));
findBusesBtn.addEventListener('click', findAvailableBuses);
themeToggleBtn.addEventListener('click', toggleTheme);
togglePanelBtn.addEventListener('click', () => panelContent.classList.toggle('hidden'));
sosBtn.addEventListener('click', () => sosModal.classList.remove('hidden'));
closeSosModalBtn.addEventListener('click', () => sosModal.classList.add('hidden'));

// --- VIEW SWITCHING LOGIC ---
function switchView(view) {
    const views = { finder: finderView, commuter: commuterView, authority: authorityView };
    const buttons = { finder: finderViewBtn, commuter: commuterViewBtn, authority: authorityViewBtn };

    // Hide all views
    Object.values(views).forEach(v => v.classList.add('hidden'));

    // Reset all buttons
    Object.values(buttons).forEach(b => {
        b.classList.remove('bg-blue-600', 'text-white', 'shadow');
        b.classList.add('text-gray-600', 'dark:text-gray-300');
    });

    // Activate selected view
    views[view].classList.remove('hidden');
    buttons[view].classList.add('bg-blue-600', 'text-white', 'shadow');
    buttons[view].classList.remove('text-gray-600', 'dark:text-gray-300');
}

// --- INITIALIZATION ---
async function main() {
    try {
        console.log("Initializing App...");

        // 1. Fetch Static Data (Routes & Stops)
        // Note: For now, we simulate fetching full route details. 
        // In a full implementation, you would have a GET /routes endpoint.
        await fetchAndProcessStaticData();

        // 2. Setup Input Listeners for Finder
        setupStopInputListeners();

        // 3. Start Live Polling (The Heart of the System)
        setInterval(fetchLiveBusData, 2000); // Poll every 2 seconds

        // Initial Fetch
        fetchLiveBusData();

    } catch (error) {
        console.error("Initialization Error:", error);
    }
}

// --- DATA FETCHING ---

/**
 * Fetches static route configuration (Paths, Stops)
 * Since the backend mainly stores logs, we reconstruct the static map data here
 * or fetch from a dedicated endpoint if available.
 */
async function fetchAndProcessStaticData() {
    try {
        console.log("Fetching static route data from API...");
        
        // 1. Fetch data from the live backend API
        const response = await fetch(`${API_BASE_URL}/routes`);
        
        // Check if the API call was successful
        if (!response.ok) {
             throw new Error(`HTTP error! Status: ${response.status}. Is API running on port 8000?`);
        }
        
        // The API returns an object like: { "routes": { "AS-1": { ... } } }
        const data = await response.json(); 

        // 2. Assign the real data to the global variable
        allRoutesData = data.routes; 
        
        // 3. Process and render the real data
        processRouteDataForUI();
        renderRouteListUI();
        
        console.log("✅ Routes loaded successfully from API.");

    } catch (e) {
        console.error("Failed to load static route data:", e);
        // Fallback UI to alert user
        const routeList = document.getElementById('route-list');
        if(routeList) {
             routeList.innerHTML = `<div class="text-sm text-center text-red-500 p-4">Error loading routes. Check console for details.</div>`;
        }
    }
}

function processRouteDataForUI() {
    allAvailableStops = [];
    stopToRoutesMap = new Map();
    const uniqueStops = new Set();

    Object.entries(allRoutesData).forEach(([routeId, routeData]) => {
        // Draw Route Polyline (Simplified straight lines for prototype)
        if (routeData.stops.length > 1) {
            const pathCoords = routeData.stops.map(s => ({ lat: s.lat, lng: s.lng }));
            const polyline = new google.maps.Polyline({
                path: pathCoords,
                geodesic: true,
                strokeColor: "#3b82f6",
                strokeOpacity: 0.6,
                strokeWeight: 5
            });
            // Don't set map yet, only when highlighted
            routePolylines[routeId] = polyline;
        }

        // Process Stops
        routeData.stops.forEach(stop => {
            if (!uniqueStops.has(stop.name)) {
                uniqueStops.add(stop.name);
                allAvailableStops.push({ name: stop.name, lat: stop.lat, lng: stop.lng });
            }
            if (!stopToRoutesMap.has(stop.name)) {
                stopToRoutesMap.set(stop.name, []);
            }
            stopToRoutesMap.get(stop.name).push(routeId);
        });
    });

    // Populate Datalist
    const datalist = document.getElementById('stops-datalist');
    if (datalist) {
        datalist.innerHTML = '';
        allAvailableStops.forEach(stop => {
            const option = document.createElement('option');
            option.value = stop.name;
            datalist.appendChild(option);
        });
    }
}

/**
 * Polls the backend for live bus positions
 */
async function fetchLiveBusData() {
    try {
        const response = await fetch(`${API_BASE_URL}/buses/live`);
        if (!response.ok) throw new Error("API Offline");

        const liveBuses = await response.json();

        const activeBusIds = new Set();
        const formattedBuses = [];

        liveBuses.forEach(bus => {
            // Backend returns: { vehicle_id, route_id, lat, lng, speed }
            const busData = {
                id: bus.vehicle_id,
                routeId: bus.route_id,
                lat: bus.lat,
                lng: bus.lng,
                speed: bus.speed,
                timestamp: new Date()
            };

            updateBusMarker(busData);
            activeBusIds.add(busData.id);
            formattedBuses.push(busData);
        });

        // Cleanup Ghost Buses
        for (const busId in busMarkers) {
            if (!activeBusIds.has(busId)) {
                busMarkers[busId].setMap(null);
                delete busMarkers[busId];
            }
        }

        // Update Fleet UI
        updateAuthorityList(formattedBuses);

        // Update ETA if a route is selected
        if (selectedRouteId) {
            // Re-trigger ETA calc if needed
        }

    } catch (error) {
        console.warn("Polling Error (Is Backend Running?):", error.message);
    }
}

// --- UI RENDERING ---

function renderRouteListUI() {
    const routeList = document.getElementById('route-list');
    routeList.innerHTML = '';

    Object.entries(allRoutesData).forEach(([routeId, routeData]) => {
        const routeElement = document.createElement('div');
        routeElement.className = 'p-3 bg-gray-50/50 dark:bg-gray-700/50 rounded-lg flex items-center justify-between cursor-pointer hover:bg-gray-100/50 dark:hover:bg-gray-600/50';
        routeElement.id = `route-item-${routeId}`;
        routeElement.innerHTML = `<p class="font-semibold text-gray-700 dark:text-gray-200">${routeData.routeName}</p><i class="fa-solid fa-chevron-right text-gray-400"></i>`;

        routeElement.addEventListener('click', () => {
            if (selectedRouteId === routeId) {
                selectedRouteId = null;
                clearRouteSelection();
                clearStopMarkers();
                document.getElementById('route-details-view').classList.add('hidden');
            } else {
                selectedRouteId = routeId;
                highlightRoute(routeId);
                showRouteDetails(routeId);
            }
        });
        routeList.appendChild(routeElement);
    });
}

function updateAuthorityList(buses) {
    const busStatusList = document.getElementById('bus-status-list');
    busStatusList.innerHTML = '';

    if (buses.length === 0) {
        busStatusList.innerHTML = `<div class="text-sm text-center text-gray-500 dark:text-gray-400 p-4">Waiting for bus data...<br><span class="text-xs">Ensure backend & simulator are running</span></div>`;
        return;
    }

    buses.sort((a, b) => (a.id).localeCompare(b.id)).forEach(bus => {
        const busElement = document.createElement('div');
        busElement.className = `p-3 rounded-lg bg-gray-50/50 dark:bg-gray-700/50 cursor-pointer hover:bg-gray-100/50 dark:hover:bg-gray-600/50`;
        busElement.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <p class="font-bold text-gray-800 dark:text-white">${allRoutesData[bus.routeId]?.routeName || bus.routeId}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400">${bus.id}</p>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500">${Math.round(bus.speed || 0)} km/h</span>
                    <div class="w-3 h-3 rounded-full blinking" style="background-color: #3b82f6"></div>
                </div>
            </div>
        `;
        busElement.addEventListener('click', () => {
            const marker = busMarkers[bus.id];
            if (marker) {
                map.panTo(marker.getPosition());
                google.maps.event.trigger(marker, 'click');
            }
        });
        busStatusList.appendChild(busElement);
    });
}

// --- MAP INTERACTION ---

function highlightRoute(routeId) {
    // Reset all lines
    Object.values(routePolylines).forEach(p => p.setMap(null));

    // Draw selected
    if (routePolylines[routeId]) {
        routePolylines[routeId].setMap(map);
        routePolylines[routeId].setOptions({ strokeColor: '#1d4ed8', strokeWeight: 6, strokeOpacity: 1, zIndex: 10 });

        // Fit bounds
        const bounds = new google.maps.LatLngBounds();
        routePolylines[routeId].getPath().forEach(latLng => bounds.extend(latLng));
        map.fitBounds(bounds);
    }

    // UI Highlight
    document.querySelectorAll('#route-list > div').forEach(el => el.classList.remove('selected-route'));
    const item = document.getElementById(`route-item-${routeId}`);
    if (item) item.classList.add('selected-route');
}

function clearRouteSelection() {
    Object.values(routePolylines).forEach(p => p.setMap(null));
    document.querySelectorAll('#route-list > div').forEach(el => el.classList.remove('selected-route'));
}

function clearStopMarkers() {
    stopMarkers.forEach(marker => marker.setMap(null));
    stopMarkers = [];
}

function showRouteDetails(routeId) {
    clearStopMarkers();
    const routeData = allRoutesData[routeId];
    if (!routeData) return;

    const routeDetailsView = document.getElementById('route-details-view');
    const stopList = document.getElementById('stop-list');
    const routeDetailsTitle = document.getElementById('route-details-title');

    routeDetailsTitle.textContent = routeData.routeName;
    stopList.innerHTML = '';
    routeDetailsView.classList.remove('hidden');

    routeData.stops.forEach((stop, index) => {
        // Create Stop Marker
        const marker = new google.maps.Marker({
            position: { lat: stop.lat, lng: stop.lng },
            map: map,
            title: stop.name,
            icon: { path: google.maps.SymbolPath.CIRCLE, scale: 5, fillColor: '#ffffff', fillOpacity: 1, strokeColor: '#3b82f6', strokeWeight: 2 }
        });
        stopMarkers.push(marker);

        // UI List Item
        const stopElement = document.createElement('div');
        stopElement.className = 'p-2 rounded-lg bg-gray-100/50 dark:bg-gray-800/50 flex justify-between items-center';
        stopElement.innerHTML = `<p class="text-sm font-semibold text-gray-700 dark:text-gray-200">${index + 1}. ${stop.name}</p>`;
        stopList.appendChild(stopElement);
    });
}

function updateBusMarker(busData) {
    const latLng = { lat: busData.lat, lng: busData.lng };

    // Custom SVG Icon for Bus
    const busIcon = {
        path: 'M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11C5.84 5 5.28 5.42 5.08 6.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z',
        fillColor: '#ffe600',
        fillOpacity: 1,
        strokeWeight: 1,
        strokeColor: document.documentElement.classList.contains('dark') ? '#000' : '#fff',
        scale: 1.2,
        anchor: new google.maps.Point(12, 12)
    };

    if (busMarkers[busData.id]) {
        busMarkers[busData.id].setPosition(latLng);
        busMarkers[busData.id].setIcon(busIcon);
        busMarkers[busData.id].set('busData', busData);
    } else {
        const marker = new google.maps.Marker({
            position: latLng,
            map: map,
            icon: busIcon,
            title: busData.id
        });
        marker.set('busData', busData);

        // Info Window Click
        marker.addListener('click', () => {
            const data = marker.get('busData');
            const content = `
                <div class="text-black">
                    <p class="font-bold text-lg">${allRoutesData[data.routeId]?.routeName || data.routeId}</p>
                    <p class="text-sm">ID: ${data.id}</p>
                    <p class="text-xs text-gray-500">Speed: ${Math.round(data.speed || 0)} km/h</p>
                </div>
            `;
            infoWindow.setContent(content);
            infoWindow.open(map, marker);
        });

        busMarkers[busData.id] = marker;
    }
}

// --- FINDER LOGIC ---

async function findAvailableBuses() {
    const startInput = document.getElementById('start-location-input');
    const endInput = document.getElementById('end-location-input');

    finderResultsList.innerHTML = `<div class="flex justify-center p-4"><div class="spinner border-t-blue-500 border-4 w-6 h-6 rounded-full"></div></div>`;

    const startStopName = startInput.value;
    const endStopName = endInput.value;

    if (!stopToRoutesMap.has(startStopName) || !stopToRoutesMap.has(endStopName)) {
        finderResultsList.innerHTML = `<p class="text-red-500 text-sm text-center">Please select valid stops.</p>`;
        return;
    }

    // Find routes that contain BOTH stops
    const startRoutes = stopToRoutesMap.get(startStopName);
    const endRoutes = stopToRoutesMap.get(endStopName);
    const validRoutes = startRoutes.filter(routeId => endRoutes.includes(routeId));

    if (validRoutes.length === 0) {
        finderResultsList.innerHTML = `<p class="text-gray-500 text-sm text-center">No direct route found.</p>`;
        return;
    }

    // Find active buses on those routes
    const activeBuses = Object.values(busMarkers)
        .map(m => m.get('busData'))
        .filter(b => validRoutes.includes(b.routeId));

    if (activeBuses.length === 0) {
        finderResultsList.innerHTML = `<p class="text-gray-500 text-sm text-center">Route exists (${validRoutes.join(', ')}), but no buses active.</p>`;
        return;
    }

    // Calculate ETAs using Client-Side Distance Matrix (Since backend doesn't have it yet)
    const startStopDetails = allAvailableStops.find(s => s.name === startStopName);
    const startLatLng = new google.maps.LatLng(startStopDetails.lat, startStopDetails.lng);

    const service = new google.maps.DistanceMatrixService();
    const origins = activeBuses.map(b => new google.maps.LatLng(b.lat, b.lng));

    service.getDistanceMatrix({
        origins: origins,
        destinations: [startLatLng],
        travelMode: 'DRIVING'
    }, (response, status) => {
        finderResultsList.innerHTML = '';
        if (status === 'OK') {
            const results = [];
            response.rows.forEach((row, i) => {
                if (row.elements[0].status === 'OK') {
                    results.push({
                        bus: activeBuses[i],
                        duration: row.elements[0].duration.text,
                        seconds: row.elements[0].duration.value
                    });
                }
            });

            results.sort((a, b) => a.seconds - b.seconds);

            results.forEach(res => {
                const el = document.createElement('div');
                el.className = 'p-3 rounded-lg bg-gray-50/50 dark:bg-gray-700/50 cursor-pointer hover:bg-gray-100/50 dark:hover:bg-gray-600/50 flex justify-between items-center';
                el.innerHTML = `
                    <div>
                        <p class="font-bold text-gray-800 dark:text-white">${allRoutesData[res.bus.routeId].routeName}</p>
                        <p class="text-xs text-gray-500">Bus: ${res.bus.id}</p>
                    </div>
                    <p class="text-sm font-semibold text-green-500">${res.duration}</p>
                `;
                el.addEventListener('click', () => {
                    const marker = busMarkers[res.bus.id];
                    if (marker) {
                        map.panTo(marker.getPosition());
                        google.maps.event.trigger(marker, 'click');
                    }
                });
                finderResultsList.appendChild(el);
            });
        }
    });
}

function setupStopInputListeners() {
    // Basic datalist filtering handled by browser
}

// --- THEMING & MAP SETUP ---

function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    if (isDark) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
        if (map) map.setOptions({ styles: lightMapStyle });
    } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
        if (map) map.setOptions({ styles: darkMapStyle });
    }
}

function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: 31.6339, lng: 74.8723 },
        zoom: 13,
        disableDefaultUI: true
    });
    infoWindow = new google.maps.InfoWindow();

    // Apply saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark');
        map.setOptions({ styles: darkMapStyle });
    } else {
        map.setOptions({ styles: lightMapStyle });
    }

    main();
}

window.initMap = initMap;

// Dynamic Script Load (To prevent exposing key in HTML if needed, though strictly client side)
(function () {
    if (GOOGLE_MAPS_API_KEY && GOOGLE_MAPS_API_KEY !== "YOUR_KEY_HERE") {
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&callback=initMap&libraries=geometry,places`;
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    } else {
        alert("Please set GOOGLE_MAPS_API_KEY in app.js");
    }
})();