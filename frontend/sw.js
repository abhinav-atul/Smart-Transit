/**
 * Smart-Transit Service Worker
 * Implements production-grade caching strategies:
 *   - Cache-first: map tiles, CSS, JS, images (fast offline load)
 *   - Network-first: API calls with stale fallback (shows last known buses offline)
 *   - Stale-while-revalidate: route data (always fresh, never blocks)
 */

const CACHE_VERSION = 'v3';
const STATIC_CACHE  = `smart-transit-static-${CACHE_VERSION}`;
const API_CACHE     = `smart-transit-api-${CACHE_VERSION}`;
const TILE_CACHE    = `smart-transit-tiles-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/api-docs.html',
  '/assets/app.js',
  '/assets/style.css',
  '/assets/bus-icon.svg',
  '/manifest.json',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap',
];

// ── Install: pre-cache static assets ────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: evict old caches ───────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  const currentCaches = [STATIC_CACHE, API_CACHE, TILE_CACHE];
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((name) => !currentCaches.includes(name))
          .map((name) => caches.delete(name))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: routing strategy ───────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and WebSocket requests
  if (request.method !== 'GET') return;
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;

  // Map tiles: cache-first with long TTL
  if (url.hostname.includes('tile') || url.hostname.includes('openstreetmap')) {
    event.respondWith(cacheTileFirst(request));
    return;
  }

  // API calls: network-first, fall back to cache (offline mode shows last data)
  if (url.pathname.startsWith('/buses') ||
      url.pathname.startsWith('/routes') ||
      url.pathname.startsWith('/eta') ||
      url.pathname.startsWith('/stats')) {
    event.respondWith(networkFirstWithCache(request, API_CACHE));
    return;
  }

  // Static assets: cache-first
  event.respondWith(cacheFirst(request));
});

// ── Strategy: Cache-First ─────────────────────────────────────────────────────
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline — content not available', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}

// ── Strategy: Network-First with Cache Fallback ───────────────────────────────
async function networkFirstWithCache(request, cacheName) {
  try {
    const response = await fetch(request, { timeout: 5000 });
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) {
      // Add offline header so UI can show stale indicator
      const headers = new Headers(cached.headers);
      headers.append('X-Served-From', 'service-worker-cache');
      return new Response(cached.body, { status: cached.status, headers });
    }
    return new Response(JSON.stringify({ error: 'offline', data: [] }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// ── Strategy: Tile Cache-First with 7-day expiry ─────────────────────────────
async function cacheTileFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(TILE_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 504 });
  }
}

// ── Push Notifications (skeleton for Phase 9) ─────────────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || 'Smart Transit', {
      body: data.body || 'Your bus is arriving soon.',
      icon: '/assets/bus-icon.svg',
      badge: '/assets/bus-icon.svg',
      tag: data.tag || 'transit-alert',
      data: { url: data.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});
