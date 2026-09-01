/* WimHof呼吸法 — オフライン用のサービスワーカー

   方針は stale-while-revalidate。
   キャッシュがあれば即座に返して起動を速くし、裏で新しい版を取りに行く。
   更新は次回の起動から反映される。呼吸中に読み込みで待たされないことを優先。

   音声もBGMも index.html の中に入っているので、これだけ持てば完全に
   オフラインで動く。Google Fonts は取れたときに一緒に貯めておく。 */

const VERSION = "v1";
const CACHE = "wimhof-" + VERSION;

const ASSETS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-192-maskable.png",
  "./icons/icon-512-maskable.png",
  "./icons/apple-touch-icon.png"
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const isFont = /(^|\.)fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (url.origin !== self.location.origin && !isFont) return;

  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req, { ignoreSearch: url.origin === self.location.origin });

    const fresh = fetch(req).then(res => {
      // opaque（Google Fonts）も status 0 で返るので ok では判定できない
      if (res && (res.ok || res.type === "opaque")) cache.put(req, res.clone());
      return res;
    }).catch(() => null);

    return hit || (await fresh) || new Response("offline", { status: 503 });
  })());
});
