const CACHE = "finora-v12";
const ASSETS = ["/", "/index.html", "/css/main.css", "/js/config.js", "/js/api.js", "/js/app.js", "/manifest.webmanifest", "/version.json", "/assets/icons/favicon.svg", "/assets/icons/icon-192.png", "/assets/icons/icon-512.png"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("message", event => { if (event.data?.type === "SKIP_WAITING") self.skipWaiting(); });
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.pathname === "/version.json") { event.respondWith(fetch(event.request, {cache:"no-store"})); return; }
  if (url.origin !== location.origin) return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
