
const CACHE_NAME = "ai-news-intelligence-v1";

const APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.json"
];

const DATA_FILES = [
  "news.json",
  "ai_briefing.md",
  "daily_briefing.md"
];

// Install: cache the main app files.
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll(APP_SHELL)
    )
  );

  self.skipWaiting();
});

// Activate: remove old caches.
self.addEventListener("activate", event => {
  event.waitUntil(
    Promise.all([
      caches.keys().then(keys =>
        Promise.all(
          keys
            .filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
        )
      ),
      self.clients.claim()
    ])
  );
});

// Fetch: use fresh data when online and cached data when offline.
self.addEventListener("fetch", event => {
  const request = event.request;

  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Do not intercept requests to external news websites.
  if (url.origin !== self.location.origin) return;

  const scope = new URL(self.registration.scope);
  if (!url.pathname.startsWith(scope.pathname)) return;

  const filename = url.pathname.split("/").pop();
  const isDataFile = DATA_FILES.includes(filename);

  event.respondWith(
    fetch(request)
      .then(response => {
        if (response.ok && response.type === "basic") {
          const copy = response.clone();

          // Cache successful responses for offline use.
          caches.open(CACHE_NAME).then(cache =>
            cache.put(request, copy)
          );
        }

        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request, {
          ignoreSearch: true
        });

        if (cached) return cached;

        if (!isDataFile && request.mode === "navigate") {
          const home = await caches.match("./index.html");
          if (home) return home;
        }

        return new Response(
          "Content unavailable while offline.",
          {
            status: 503,
            headers: {
              "Content-Type": "text/plain"
            }
          }
        );
      })
  );
});
