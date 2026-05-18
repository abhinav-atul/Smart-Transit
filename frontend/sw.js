const CACHE_NAME = 'smart-transit-v1';
const STATIC_ASSETS = ['/', '/index.html', '/assets/app.js', '/assets/style.css', '/assets/bus-icon.svg'];

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
});

self.addEventListener('fetch', (event) => {
    // Cache-first for static assets, network-first for API calls
    if (event.request.url.includes('/api') || event.request.url.includes('/buses') || event.request.url.includes('/routes')) {
        event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
    } else {
        event.respondWith(caches.match(event.request).then(r => r || fetch(event.request)));
    }
});
