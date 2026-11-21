const VERSAO = 'hinario-v4';
const CASCA = ['/', '/index.html', '/manifest.webmanifest', '/data/catalogo.json', '/icons/icone-192.png'];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(VERSAO).then((c) => c.addAll(CASCA)).then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((chaves) => Promise.all(chaves.filter((k) => k !== VERSAO).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request;
  if (pedido.method !== 'GET') return;

  const url = new URL(pedido.url);
  const ehPagina = pedido.mode === 'navigate';
  const ehImagem = /\.(jpe?g|png|webp|gif|svg)$/i.test(url.pathname) || url.pathname.startsWith('/manus-storage/');
  const ehDado = url.pathname.endsWith('/data/catalogo.json');

  if (ehPagina) {
    evento.respondWith(
      fetch(pedido)
        .then((resposta) => {
          const copia = resposta.clone();
          caches.open(VERSAO).then((c) => c.put('/index.html', copia));
          return resposta;
        })
        .catch(() => caches.match('/index.html').then((r) => r || Response.error())),
    );
    return;
  }

  if (ehDado) {
    evento.respondWith(
      fetch(pedido)
        .then((resposta) => {
          const copia = resposta.clone();
          caches.open(VERSAO).then((c) => c.put(pedido, copia));
          return resposta;
        })
        .catch(() => caches.match(pedido).then((r) => r || caches.match('/data/catalogo.json'))),
    );
    return;
  }

  if (ehImagem) {
    evento.respondWith(
      caches.match(pedido).then(
        (emCache) =>
          emCache ||
          fetch(pedido).then((resposta) => {
            if (resposta.ok) {
              const copia = resposta.clone();
              caches.open(VERSAO).then((c) => c.put(pedido, copia));
            }
            return resposta;
          }),
      ),
    );
    return;
  }

  evento.respondWith(
    caches.match(pedido).then((emCache) => {
      const rede = fetch(pedido)
        .then((resposta) => {
          if (resposta.ok && url.origin === self.location.origin) {
            const copia = resposta.clone();
            caches.open(VERSAO).then((c) => c.put(pedido, copia));
          }
          return resposta;
        })
        .catch(() => emCache);
      return emCache || rede;
    }),
  );
});
