/* 2026 글로벌 주가 대시보드 · 서비스 워커
 * - 앱 셸(html/css/js/아이콘): 캐시 우선(stale-while-revalidate)
 * - 데이터(data/data.json): 네트워크 우선, 실패 시 캐시 폴백
 * CACHE 버전을 올리면 이전 캐시는 activate 단계에서 정리된다.
 */
"use strict";

const CACHE = "stock-dash-v2";
const SHELL = [
  "./",
  "./index.html",
  "./assets/style.css",
  "./assets/app.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // 외부 요청은 패스

  // 데이터: 네트워크 우선 → 캐시 폴백
  if (url.pathname.endsWith("/data/data.json")) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // 앱 셸 및 기타 동일 출처 GET: 캐시 우선 + 백그라운드 갱신
  e.respondWith(
    caches.match(req).then((cached) => {
      const fetched = fetch(req)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || fetched;
    })
  );
});
