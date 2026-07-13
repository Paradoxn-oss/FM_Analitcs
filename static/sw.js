// static/sw.js
//
// Service worker do FM Scouting (item 18 do roadmap). É servido na raiz do
// site (rota /sw.js em app.py), não em /static/sw.js — necessário para que
// o escopo padrão do service worker cubra o site inteiro ("/"), já que o
// escopo máximo de um service worker é, por padrão, a pasta onde ele mora.
//
// O app depende de sessão + processamento no servidor (upload, cálculo de
// métricas), então não faz sentido tentar funcionar 100% offline. O que
// este service worker faz é só cachear os arquivos estáticos essenciais
// (CSS, JS, ícones) pra evitar buscar tudo de novo na rede a cada
// navegação — e, junto com o manifest.json, permitir "instalar" o app.

const CACHE_NOME = "fm-scouting-v1";

const ARQUIVOS_ESSENCIAIS = [
    "/static/style.css",
    "/static/script.js",
    "/static/dropzone.js",
    "/static/elenco.js",
    "/static/favicon.ico",
    "/static/favicon-16x16.png",
    "/static/favicon-32x32.png",
    "/static/apple-touch-icon.png",
    "/static/icon-192.png",
    "/static/icon-512.png",
];

self.addEventListener("install", function(event) {
    event.waitUntil(
        caches.open(CACHE_NOME).then(function(cache) {
            return cache.addAll(ARQUIVOS_ESSENCIAIS);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", function(event) {
    // Limpa caches de versões antigas (ex: depois de trocar CACHE_NOME
    // numa próxima versão do service worker).
    event.waitUntil(
        caches.keys().then(function(chaves) {
            return Promise.all(
                chaves
                    .filter(function(chave) { return chave !== CACHE_NOME; })
                    .map(function(chave) { return caches.delete(chave); })
            );
        })
    );
    self.clients.claim();
});

// Estratégia "cache, com atualização em segundo plano" — só para os
// arquivos estáticos essenciais acima. Páginas HTML (rotas do Flask) e
// chamadas AJAX (perfil customizado, jogadores parecidos etc.) sempre
// passam direto pela rede, sem interceptação, porque dependem do estado
// da sessão no servidor.
self.addEventListener("fetch", function(event) {
    const url = new URL(event.request.url);
    if (!ARQUIVOS_ESSENCIAIS.includes(url.pathname)) return;

    event.respondWith(
        caches.match(event.request).then(function(respostaCache) {
            const buscaNaRede = fetch(event.request)
                .then(function(respostaRede) {
                    caches.open(CACHE_NOME).then(function(cache) {
                        cache.put(event.request, respostaRede.clone());
                    });
                    return respostaRede;
                })
                .catch(function() { return respostaCache; });

            return respostaCache || buscaNaRede;
        })
    );
});
