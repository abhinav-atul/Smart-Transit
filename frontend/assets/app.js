// --- CONFIGURATION ---
const API_BASE_URL = "http://localhost:8000";
const BUS_ICON_URL = "https://img.icons8.com/?size=100&id=15158&format=png&color=000000";

const TILE_LAYERS = {
    dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    light: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
};

// --- GLOBALS ---
let map;
let currentTileLayer = null;
let busMarkers = {};        
let routePolylines = {};    
let stopMarkers = [];       
let userLocationMarker = null;
let markerAnimFrames = {}; 
let allRoutesData = {};
let allAvailableStops = []; // Array of { name, lat, lng }
let stopToRoutesMap = new Map();
let selectedRouteId = null;
let selectedBusId = null;

// --- DOM ELEMENTS ---
const finderBtn = document.getElementById('finder-view-btn');
const commuterBtn = document.getElementById('commuter-view-btn');
const authorityBtn = document.getElementById('authority-view-btn');
const finderView = document.getElementById('finder-view');
const commuterView = document.getElementById('commuter-view');
const authorityView = document.getElementById('authority-view');

const startInput = document.getElementById('start-location-input');
const endInput = document.getElementById('end-location-input');
const clearStartBtn = document.getElementById('clear-start-btn');
const clearEndBtn = document.getElementById('clear-end-btn');
const swapBtn = document.getElementById('swap-locations-btn');
const findBusesBtn = document.getElementById('find-buses-btn');
const finderResultsList = document.getElementById('finder-results-list');

const routeList = document.getElementById('route-list');
const busStatusList = document.getElementById('bus-status-list');

const selectedBusCard = document.getElementById('selected-bus-card');
const busDetailId = document.getElementById('bus-detail-id');
const busDetailSpeed = document.getElementById('bus-detail-speed');
const busDetailNextStop = document.getElementById('bus-detail-next-stop');
const busDetailEta = document.getElementById('bus-detail-eta');

const sosModal = document.getElementById('sos-modal');
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const userLocBtn = document.getElementById('user-location-btn');
const stopsDatalist = document.getElementById('stops-datalist');


// --- INITIALIZATION ---
function initMap() {
    map = L.map('map', { zoomControl: false, attributionControl: false }).setView([31.6339, 74.8723], 13);
    const isDark = document.documentElement.classList.contains('dark');
    setMapTheme(isDark ? 'dark' : 'light');
    main();
}

async function main() {
    await fetchAndProcessStaticData();
    setInterval(fetchLiveBusData, 2000); 
    fetchLiveBusData(); 
}

// --- THEME ---
themeToggleBtn.addEventListener('click', () => {
    const html = document.documentElement;
    const isDark = html.classList.toggle('dark');
    setMapTheme(isDark ? 'dark' : 'light');
    themeToggleBtn.querySelector('i').className = isDark ? 'fa-solid fa-moon' : 'fa-solid fa-sun text-yellow-500';
});

function setMapTheme(theme) {
    if (currentTileLayer) map.removeLayer(currentTileLayer);
    currentTileLayer = L.tileLayer(TILE_LAYERS[theme], {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd', maxZoom: 20
    }).addTo(map);
}

// --- DATA ---
async function fetchAndProcessStaticData() {
    try {
        const response = await fetch(`${API_BASE_URL}/routes`);
        if (!response.ok) throw new Error("API Offline");
        const data = await response.json();
        allRoutesData = data.routes;
        processRouteDataForUI();
        renderRouteListUI();
    } catch (e) {
        routeList.innerHTML = `<div class="p-4 rounded-xl bg-red-50 text-red-600 text-sm">Failed to load routes.</div>`;
    }
}

function processRouteDataForUI() {
    stopsDatalist.innerHTML = '';
    allAvailableStops = []; // Reset global stops array
    stopToRoutesMap = new Map();

    Object.entries(allRoutesData).forEach(([routeId, routeData]) => {
        if (routeData.stops.length > 1) {
            const pathCoords = routeData.stops.map(s => [s.lat, s.lng]);
            routePolylines[routeId] = L.polyline(pathCoords, { color: '#3b82f6', weight: 5, opacity: 0.8 });
            
            fetchRouteShape(routeData.stops).then(latLngs => {
                if (latLngs && routePolylines[routeId]) routePolylines[routeId].setLatLngs(latLngs);
            });
        }
        routeData.stops.forEach(stop => {
            if (!stopToRoutesMap.has(stop.name)) {
                allAvailableStops.push({ name: stop.name, lat: stop.lat, lng: stop.lng }); // Store for ETA calc
                
                const option = document.createElement('option');
                option.value = stop.name;
                stopsDatalist.appendChild(option);
                stopToRoutesMap.set(stop.name, []);
            }
            stopToRoutesMap.get(stop.name).push(routeId);
        });
    });
}

async function fetchRouteShape(stops) {
    if (!stops || stops.length < 2) return null;
    const coordinates = stops.map(s => `${s.lng},${s.lat}`).join(';');
    try {
        const url = `https://router.project-osrm.org/route/v1/driving/${coordinates}?overview=full&geometries=geojson`;
        const res = await fetch(url);
        if (res.ok) {
            const data = await res.json();
            if (data.routes?.[0]) return data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
        }
    } catch (e) {}
    return null;
}

async function fetchLiveBusData() {
    try {
        const res = await fetch(`${API_BASE_URL}/buses/live`);
        if (!res.ok) return;
        const liveBuses = await res.json();
        const activeBusIds = new Set();
        const formattedBuses = [];

        liveBuses.forEach(bus => {
            const busData = { id: bus.vehicle_id, routeId: bus.route_id, lat: bus.lat, lng: bus.lng, speed: bus.speed };
            updateBusMarker(busData);
            activeBusIds.add(busData.id);
            formattedBuses.push(busData);
        });

        for (const busId in busMarkers) {
            if (!activeBusIds.has(busId)) {
                map.removeLayer(busMarkers[busId]);
                delete busMarkers[busId];
            }
        }
        updateAuthorityList(formattedBuses);
    } catch (e) {}
}

// --- BUS SELECTION LOGIC ---

function selectBus(busData) {
    selectedBusId = busData.id;
    switchView('commuter');
    toggleRouteSelection(busData.routeId);
    selectedBusCard.classList.remove('hidden');
    updateBusDetailCard(busData);
}

function updateBusDetailCard(busData) {
    if (!busData) return;
    
    // Calculate ETA
    const route = allRoutesData[busData.routeId];
    let etaText = "-- min";
    let nextStopName = "Calculating...";

    if (route) {
        let minDist = Infinity;
        let nearest = null;
        const busLatLng = L.latLng(busData.lat, busData.lng);

        route.stops.forEach(stop => {
            const stopLatLng = L.latLng(stop.lat, stop.lng);
            const dist = busLatLng.distanceTo(stopLatLng);
            if (dist < minDist) {
                minDist = dist;
                nearest = stop;
            }
        });

        if (nearest) {
            nextStopName = nearest.name;
            const speed = Math.max(busData.speed, 30);
            const seconds = minDist / (speed * 1000 / 3600);
            etaText = minDist < 50 ? "Arrived" : `${Math.ceil(seconds / 60)} min`;
        }
    }

    busDetailId.textContent = busData.id;
    busDetailSpeed.textContent = `${Math.round(busData.speed)} km/h`;
    busDetailNextStop.textContent = nextStopName;
    busDetailEta.textContent = etaText;
}

function updateBusMarker(busData) {
    const busIcon = L.icon({
        iconUrl: BUS_ICON_URL, iconSize: [50, 50], iconAnchor: [25, 25]
    });

    if (busMarkers[busData.id]) {
        animateMarkerTo(busMarkers[busData.id], busData.lat, busData.lng);
        if (selectedBusId === busData.id) {
            updateBusDetailCard(busData);
        }
    } else {
        const marker = L.marker([busData.lat, busData.lng], {
            icon: busIcon, busId: busData.id, busData: busData
        }).addTo(map);

        marker.on('click', () => selectBus(busData));
        busMarkers[busData.id] = marker;
    }
}

function animateMarkerTo(marker, newLat, newLng, duration = 2000) {
    const startPos = marker.getLatLng();
    const startLat = startPos.lat;
    const startLng = startPos.lng;
    const startTime = performance.now();
    const busId = marker.options.busId;

    if (busId && markerAnimFrames[busId]) cancelAnimationFrame(markerAnimFrames[busId]);

    function step(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        marker.setLatLng([startLat + (newLat - startLat) * progress, startLng + (newLng - startLng) * progress]);
        if (progress < 1) {
            markerAnimFrames[busId] = requestAnimationFrame(step);
        } else {
            delete markerAnimFrames[busId];
        }
    }
    markerAnimFrames[busId] = requestAnimationFrame(step);
}

// --- ROUTE & VIEW LOGIC ---

function toggleRouteSelection(routeId) {
    const isSelected = selectedRouteId === routeId;
    
    if (selectedRouteId && routePolylines[selectedRouteId]) {
        map.removeLayer(routePolylines[selectedRouteId]);
        document.getElementById(`route-item-${selectedRouteId}`)?.classList.remove('border-blue-500', 'bg-blue-50', 'dark:border-brand-500', 'dark:bg-brand-900/20');
    }
    stopMarkers.forEach(m => map.removeLayer(m)); 
    stopMarkers = [];
    document.getElementById('route-details-view').classList.add('hidden');

    if (isSelected && !selectedBusId) { 
        selectedRouteId = null; 
        return; 
    }
    
    selectedRouteId = routeId;
    const poly = routePolylines[routeId];
    if (poly) {
        poly.addTo(map);
        map.fitBounds(poly.getBounds(), { padding: [50, 50] });
    }
    
    const item = document.getElementById(`route-item-${routeId}`);
    if (item) item.classList.add('border-blue-500', 'bg-blue-50', 'dark:border-brand-500', 'dark:bg-brand-900/20');

    document.getElementById('route-details-view').classList.remove('hidden');
    document.getElementById('route-details-title').textContent = allRoutesData[routeId].routeName;
    
    renderStopTimeline(routeId);
}

function renderStopTimeline(routeId) {
    const stopListEl = document.getElementById('stop-list');
    stopListEl.innerHTML = '';
    
    allRoutesData[routeId].stops.forEach((stop, idx) => {
        const marker = L.circleMarker([stop.lat, stop.lng], {
            radius: 6, fillColor: "#1e293b", fillOpacity: 1, color: "#3b82f6", weight: 2
        }).addTo(map);
        marker.bindPopup(`<b>${stop.name}</b>`);
        stopMarkers.push(marker);
        
        const isLast = idx === allRoutesData[routeId].stops.length - 1;
        const html = `
            <div class="relative ${!isLast ? 'pb-6' : ''}">
                 ${!isLast ? '<div class="absolute left-[-21px] top-2 bottom-0 w-0.5 bg-slate-300 dark:bg-white/10"></div>' : ''}
                 <div class="absolute left-[-25px] top-1 w-2.5 h-2.5 rounded-full bg-slate-400 dark:bg-slate-600 ring-4 ring-slate-100 dark:ring-gray-900"></div>
                 <p class="text-sm text-slate-700 dark:text-slate-300 font-medium">${stop.name}</p>
                 <p class="text-[10px] text-slate-400 dark:text-slate-500">Stop #${idx + 1}</p>
            </div>
        `;
        stopListEl.insertAdjacentHTML('beforeend', html);
    });
}

function renderRouteListUI() {
    routeList.innerHTML = '';
    Object.entries(allRoutesData).forEach(([routeId, routeData]) => {
        const el = document.createElement('div');
        el.className = 'group p-4 rounded-xl cursor-pointer transition-all duration-200 flex items-center justify-between border bg-white border-slate-100 hover:border-blue-200 hover:shadow-md dark:bg-white/5 dark:border-white/5 dark:hover:bg-white/10 dark:hover:border-brand-500/30 dark:shadow-none';
        el.id = `route-item-${routeId}`;
        el.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm bg-blue-50 text-blue-600 dark:bg-brand-500/20 dark:text-brand-500">${routeId.replace('AS-', '')}</div>
                <div><h4 class="font-semibold text-sm text-slate-800 dark:text-slate-200">${routeData.routeName}</h4></div>
            </div>
            <i class="fa-solid fa-chevron-right text-slate-300 dark:text-slate-600 group-hover:text-blue-500 dark:group-hover:text-brand-500"></i>
        `;
        el.addEventListener('click', () => {
            selectedBusId = null;
            selectedBusCard.classList.add('hidden');
            toggleRouteSelection(routeId);
        });
        routeList.appendChild(el);
    });
}

function updateAuthorityList(buses) {
    busStatusList.innerHTML = '';
    if (buses.length === 0) {
        busStatusList.innerHTML = `<div class="text-center py-6 text-slate-400 text-sm">No active buses.</div>`;
        return;
    }
    buses.sort((a, b) => (a.id).localeCompare(b.id)).forEach(bus => {
        const el = document.createElement('div');
        el.className = 'p-3 rounded-xl flex items-center justify-between cursor-pointer border bg-white border-slate-100 hover:bg-slate-50 dark:bg-white/5 dark:border-white/5 dark:hover:bg-white/10';
        el.innerHTML = `
            <div class="flex items-center gap-3">
                 <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                 <div><p class="font-bold text-sm text-slate-800 dark:text-slate-200">${bus.id}</p></div>
            </div>
            <span class="text-xs font-mono text-blue-600 dark:text-blue-400 font-semibold">${Math.round(bus.speed)} km/h</span>
        `;
        el.addEventListener('click', () => {
             if (busMarkers[bus.id]) {
                 map.flyTo(busMarkers[bus.id].getLatLng(), 16);
                 selectBus(bus);
             }
        });
        busStatusList.appendChild(el);
    });
}

// --- FINDER LOGIC (UPDATED TO SHOW BUSES) ---

findBusesBtn.addEventListener('click', () => {
    finderResultsList.innerHTML = `<div class="flex justify-center p-4"><i class="fa-solid fa-circle-notch fa-spin text-blue-500"></i></div>`;
    
    const sName = startInput.value;
    const eName = endInput.value;
    const sRoutes = stopToRoutesMap.get(sName) || [];
    const eRoutes = stopToRoutesMap.get(eName) || [];
    const commonRoutes = sRoutes.filter(r => eRoutes.includes(r));
    
    finderResultsList.innerHTML = '';

    if (commonRoutes.length === 0) {
        finderResultsList.innerHTML = `<div class="text-center p-3 text-sm text-slate-400">No direct route found.</div>`;
        return;
    }

    // Find active buses on these routes
    const activeBusesOnRoute = [];
    
    // Get Coordinates of Start Stop for ETA
    const startStopData = allAvailableStops.find(s => s.name === sName);
    const startLatLng = startStopData ? L.latLng(startStopData.lat, startStopData.lng) : null;

    Object.values(busMarkers).forEach(marker => {
        const bus = marker.options.busData;
        if (commonRoutes.includes(bus.routeId)) {
            // Calculate ETA to Start Stop
            let etaSeconds = 0;
            let etaText = "--";
            
            if (startLatLng) {
                const busLatLng = marker.getLatLng();
                const dist = busLatLng.distanceTo(startLatLng);
                const speed = Math.max(bus.speed, 30); // fallback speed
                etaSeconds = dist / (speed * 1000 / 3600);
                etaText = dist < 100 ? "Arriving" : `${Math.ceil(etaSeconds / 60)} min`;
            }

            activeBusesOnRoute.push({
                bus: bus,
                eta: etaText,
                etaSec: etaSeconds
            });
        }
    });

    if (activeBusesOnRoute.length === 0) {
        finderResultsList.innerHTML = `<div class="text-center p-3 text-sm text-slate-400">Route exists, but no buses active.</div>`;
        return;
    }

    // Sort by ETA (soonest first)
    activeBusesOnRoute.sort((a, b) => a.etaSec - b.etaSec);

    activeBusesOnRoute.forEach(item => {
        const bus = item.bus;
        const route = allRoutesData[bus.routeId];
        
        const el = document.createElement('div');
        el.className = 'p-4 rounded-xl flex justify-between items-center cursor-pointer border bg-blue-50 border-blue-100 hover:shadow-md dark:bg-white/5 dark:border-white/10';
        el.innerHTML = `
            <div>
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-[10px] font-bold bg-blue-200 text-blue-800 px-1.5 py-0.5 rounded dark:bg-blue-900 dark:text-blue-200">${bus.id}</span>
                    <p class="text-blue-500 text-xs font-bold uppercase">To ${eName}</p>
                </div>
                <h4 class="font-bold text-slate-800 dark:text-white">${route.routeName}</h4>
            </div>
            <div class="text-right">
                <p class="text-lg font-bold text-slate-800 dark:text-white">${item.eta}</p>
                <p class="text-xs text-green-600 dark:text-green-400 font-semibold">from ${sName}</p>
            </div>
        `;
        el.addEventListener('click', () => {
            selectBus(bus); // Open Bus Details directly
        });
        finderResultsList.appendChild(el);
    });
});

// --- OTHER UTILS ---
window.switchView = function(viewName) {
    [finderView, commuterView, authorityView].forEach(v => v.classList.add('hidden'));
    [finderBtn, commuterBtn, authorityBtn].forEach(b => b.classList.remove('active'));
    document.getElementById(`${viewName}-view`).classList.remove('hidden');
    document.getElementById(`${viewName}-view-btn`).classList.add('active');
};

userLocBtn.addEventListener('click', () => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            map.flyTo([pos.coords.latitude, pos.coords.longitude], 15);
        });
    }
});

swapBtn.addEventListener('click', () => {
    const temp = startInput.value; startInput.value = endInput.value; endInput.value = temp;
    toggleClearBtn(startInput, clearStartBtn);
    toggleClearBtn(endInput, clearEndBtn);
});

function toggleClearBtn(input, btn) {
    if (input.value.length > 0) btn.classList.remove('hidden'); else btn.classList.add('hidden');
}
[startInput, endInput].forEach(input => {
    const btn = input === startInput ? clearStartBtn : clearEndBtn;
    input.addEventListener('input', () => toggleClearBtn(input, btn));
    btn.addEventListener('click', () => { input.value = ''; input.focus(); btn.classList.add('hidden'); });
});

document.getElementById('sos-btn').addEventListener('click', () => sosModal.classList.remove('hidden'));
document.getElementById('close-sos-modal-btn').addEventListener('click', () => sosModal.classList.add('hidden'));

initMap();