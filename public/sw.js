// Hinário da Igreja — funciona sem internet.
// APP: arquivos do aplicativo (trocados a cada versão). MIDIAS: fotos das folhas (nunca apagadas numa atualização).
const VERSAO = 'v30';
const APP = 'hinario-app-' + VERSAO;
const MIDIAS = 'hinario-midias';
const ESPERA_REDE = 4000; // se a internet estiver lenta, usa o que já está salvo

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    (async () => {
      const c = await caches.open(APP);
      const base = ['/', '/index.html', '/manifest.webmanifest', '/data/catalogo.json', '/icons/icone-192.png', '/icons/icone-512.png'];
      await Promise.all(base.map((u) => c.add(new Request(u, { cache: 'reload' })).catch(() => {})));
      try {
        const lista = await (await fetch('/precache.json', { cache: 'reload' })).json();
        await Promise.all(lista.map((u) => c.add(new Request(u, { cache: 'reload' })).catch(() => {})));
      } catch (e) {
        /* sem lista: os arquivos são guardados quando forem usados */
      }
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    (async () => {
      const midias = await caches.open(MIDIAS);
      for (const nome of await caches.keys()) {
        if (nome === APP || nome === MIDIAS) continue;
        // versões antigas: aproveita as fotos já baixadas e apaga o resto
        if (/^hinario-v\d+$/.test(nome)) {
          const antigo = await caches.open(nome);
          for (const req of await antigo.keys()) {
            if (new URL(req.url).pathname.startsWith('/midias/')) {
              const r = await antigo.match(req);
              if (r) await midias.put(req, r);
            }
          }
        }
        await caches.delete(nome);
      }
      await self.clients.claim();
    })(),
  );
});

function comEspera(promessaRede, emCache) {
  // devolve a rede, mas se demorar demais e houver cópia salva, usa a cópia
  return new Promise((resolve, reject) => {
    let fim = false;
    const t = setTimeout(async () => {
      const c = await emCache();
      if (c && !fim) {
        fim = true;
        resolve(c);
      }
    }, ESPERA_REDE);
    promessaRede.then(
      (r) => {
        clearTimeout(t);
        if (!fim) {
          fim = true;
          resolve(r);
        }
      },
      async (e) => {
        clearTimeout(t);
        const c = await emCache();
        if (!fim) {
          fim = true;
          c ? resolve(c) : reject(e);
        }
      },
    );
  });
}

async function guardar(nomeCache, pedido, resposta) {
  if (resposta && resposta.ok) {
    const c = await caches.open(nomeCache);
    await c.put(pedido, resposta.clone());
  }
  return resposta;
}

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request;
  if (pedido.method !== 'GET') return;
  const url = new URL(pedido.url);
  if (url.origin !== self.location.origin) return;

  // abrir o app (qualquer endereço do app)
  if (pedido.mode === 'navigate') {
    evento.respondWith(
      comEspera(
        fetch(pedido).then((r) => guardar(APP, '/index.html', r)),
        async () => (await caches.match('/index.html')) || (await caches.match('/')),
      ).catch(() => Response.error()),
    );
    return;
  }

  // lista de músicas
  if (url.pathname === '/data/catalogo.json') {
    evento.respondWith(
      comEspera(
        fetch(pedido).then((r) => guardar(APP, '/data/catalogo.json', r)),
        () => caches.match('/data/catalogo.json'),
      ).catch(() => Response.error()),
    );
    return;
  }

  // PDFs: o leitor de PDF pede "pedaços" (Range); entrega do arquivo salvo
  if (url.pathname.startsWith('/midias/pdf/') && pedido.headers.get('range')) {
    evento.respondWith(
      (async () => {
        let salvo = await caches.match(url.pathname, { ignoreSearch: true });
        if (!salvo) {
          try {
            const r = await fetch(url.pathname);
            salvo = await guardar(MIDIAS, url.pathname, r);
          } catch (e) {
            return Response.error();
          }
        }
        const m = /bytes=(\d*)-(\d*)/.exec(pedido.headers.get('range'));
        const buf = await salvo.clone().arrayBuffer();
        const ini = m && m[1] ? parseInt(m[1], 10) : 0;
        const fim = m && m[2] ? Math.min(parseInt(m[2], 10), buf.byteLength - 1) : buf.byteLength - 1;
        return new Response(buf.slice(ini, fim + 1), {
          status: 206,
          headers: {
            'Content-Type': 'application/pdf',
            'Content-Range': `bytes ${ini}-${fim}/${buf.byteLength}`,
            'Content-Length': String(fim - ini + 1),
          },
        });
      })(),
    );
    return;
  }

  // fotos das folhas: o que já está salvo abre na hora
  if (url.pathname.startsWith('/midias/')) {
    evento.respondWith(
      caches.match(pedido, { ignoreSearch: true }).then(
        (salvo) => salvo || fetch(pedido).then((r) => guardar(MIDIAS, pedido, r)),
      ),
    );
    return;
  }

  // demais arquivos do app: usa o salvo e atualiza em segundo plano
  evento.respondWith(
    caches.match(pedido).then((salvo) => {
      const rede = fetch(pedido)
        .then((r) => guardar(APP, pedido, r))
        .catch(() => salvo || Response.error());
      return salvo || rede;
    }),
  );
});
