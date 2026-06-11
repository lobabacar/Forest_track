const CACHE_NAME = 'bea-portal-v1';

// Fichiers mis en cache pour le mode hors ligne
const FICHIERS_CACHE = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/img/logo_bea.png',
  '/static/img/icon-192x192.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
];

// Installation — mise en cache des ressources statiques
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(FICHIERS_CACHE))
      .then(() => self.skipWaiting())
  );
});

// Activation — nettoyage des anciens caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Interception des requêtes — stratégie Network First
self.addEventListener('fetch', event => {
  // Ne pas intercepter les appels API et POST
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/api/')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Mettre en cache la réponse fraîche
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() =>
        // Hors ligne — servir depuis le cache
        caches.match(event.request).then(cached =>
          cached || caches.match('/')
        )
      )
  );
});