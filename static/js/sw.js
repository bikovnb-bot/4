const CACHE_NAME = 'requests-pwa-v1';
const urlsToCache = [
  '/',
  '/requests/',
  '/accounts/login/',
  '/static/css/bootstrap.min.css',
  '/static/css/custom.css',
  '/static/js/bootstrap.bundle.min.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .catch(err => console.log('Cache addAll error', err))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
      .catch(() => {
        // Если нет сети и нет кэша, можно вернуть fallback-страницу (опционально)
        return caches.match('/');
      })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.map(key => {
        if (key !== CACHE_NAME) return caches.delete(key);
      })
    ))
  );
});