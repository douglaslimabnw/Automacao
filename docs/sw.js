/* Bolso em Dia — service worker: guarda o app para funcionar sem internet.
   Os DADOS do usuário ficam no localStorage, nunca neste cache. */
const VERSAO = "Bolso-v2";
const ARQUIVOS = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "icon-192.png", "icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSAO).then((c) => c.addAll(ARQUIVOS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // dados pessoais e requisições externas (CDN do leitor de PDF): só rede
  if (url.pathname.endsWith("dados-pessoais.json") || url.origin !== location.origin) return;
  e.respondWith(
    caches.match(e.request).then((cache) => {
      const rede = fetch(e.request)
        .then((resposta) => {
          if (resposta.ok) {
            const copia = resposta.clone();
            caches.open(VERSAO).then((c) => c.put(e.request, copia));
          }
          return resposta;
        })
        .catch(() => cache);
      return cache || rede;
    })
  );
});
