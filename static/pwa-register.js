// static/pwa-register.js
//
// Registra o service worker (ver static/sw.js e a rota /sw.js em app.py)
// para permitir instalar o FM Scouting como app (PWA) e cachear os
// arquivos estáticos essenciais. Incluído no fim de todas as páginas
// (home.html, upload.html, elenco.html, resultado.html).
if ("serviceWorker" in navigator) {
    window.addEventListener("load", function() {
        navigator.serviceWorker.register("/sw.js").catch(function(erro) {
            // Não bloqueia nada se falhar (ex: navegador sem suporte,
            // ambiente sem HTTPS em produção) — só registra no console.
            console.warn("Não foi possível registrar o service worker:", erro);
        });
    });
}
