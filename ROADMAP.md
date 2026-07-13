# Roadmap — FM Scouting

> Histórico de progresso do projeto, organizado pelas mesmas fases do
> planejamento original. Itens concluídos ficam marcados com `[x]`; os
> demais seguem como próximos passos. Para o prompt original (que ainda
> é útil como referência de contexto/arquivos ao atacar um item novo),
> veja `ROADMAP_FM_SCOUTING.md`.

---

## Fase 1 — Segurança e robustez

- [x] **1. Validar `export_id` em `/historico/comparar`** — formato
      validado com regex (`PADRAO_EXPORT_ID.fullmatch`) em
      `scouting/sessao.py` antes de qualquer acesso a arquivo.
- [x] **2. Limpeza por idade em `session_cache/`** — script versionado
      `scripts/limpar_sessoes_antigas.py` (com `--dry-run`, `--dias`,
      `--pasta`), coberto por `tests/test_limpar_sessoes_antigas.py`.
- [x] **3. Rate limiting no `/upload`** — `flask-limiter` limitando a
      rota (ver `app.py`, `limiter`).

## Fase 2 — Performance

- [ ] **4/5. Cache do ranking calculado** (Flask-Caching) — ainda não
      iniciado.
- [x] **6. Paginação nas tabelas de categoria e ranking por perfil** —
      `configurarPaginacao()`/`atualizarPaginacao()` em
      `static/script.js`, com `linha-pagina-oculta` independente do
      filtro (`linha-oculta`); controles "‹ Anterior / Página X de Y /
      Próxima ›" abaixo de cada tabela.
- [ ] **7. Processamento assíncrono para uploads grandes** — ainda não
      iniciado; vale medir o tempo de resposta atual antes de decidir se
      compensa.

## Fase 3 — Produto / novas funcionalidades

- [x] **8. Upload mais amigável (drag & drop + feedback)** —
      `static/dropzone.js` (função compartilhada `configurarDropzone`)
      liga o arrastar-e-soltar de verdade em `upload.html` e
      `elenco.html`; `app.py`/`resultado.html` mostram nome do arquivo,
      formato, linhas lidas, jogadores válidos e tempo de processamento.
- [x] **9. Upload do elenco do próprio clube** — rota `/elenco` +
      `/elenco/upload` + `/elenco/comparar`, com comparador
      jogador-escoutado × elenco (por jogador específico ou média do
      elenco). *(Encontrado já implementado ao abrir o projeto nesta
      sessão de roadmap — sem registro de quando foi feito; vale
      conferir se `scouting/sessao.py` já cobre tudo que o plano
      original previa.)*
- [ ] **10. Benchmark comparativo** (média/percentis da liga a partir do
      próprio export) — ainda não iniciado. Lembrete do plano original:
      Top Europa/Mundial não são viáveis sem uma fonte de dados externa.

## Fase 4 — GitHub / maturidade do repositório

- [ ] **11. README com GIF do projeto + screenshots** — texto do
      `README.md` corrigido (a menção a "tema claro/escuro" estava
      desatualizada — o tema claro foi removido, só existe o escuro
      "Central Tática") e uma seção `## Capturas de tela` já preparada
      com instruções de como gravar/inserir. **As imagens em si ainda
      não foram capturadas** — depende de rodar o app com um export real
      e navegar pela tela, o que não é algo que dá pra gerar sem uma
      sessão de navegador de verdade.
- [x] **12. Roadmap (To-do) no repo** — este arquivo.
- [x] **13. `CONTRIBUTING.md`** — como rodar local, rodar os testes,
      convenção de commit, como adicionar uma métrica nova.
- [x] **14. Licença destacada** — `LICENSE` (MIT). *Falta só trocar
      `[seu nome aqui]` pelo nome/organização que você quiser usar.*
- [x] **15. Seção de deploy e arquitetura no README** — nova seção
      `## Deploy e arquitetura` linkando e resumindo o `DEPLOY.md`
      existente.

## Fase 5 — Acessibilidade / alcance

- [x] **17. Meta tags OpenGraph** — `og:title`, `og:description`,
      `og:image` (usa `apple-touch-icon.png` como imagem, já que não há
      uma arte de capa própria ainda) e `twitter:card` nas 4 páginas
      (`home.html`, `upload.html`, `elenco.html`, `resultado.html`).
- [x] **18. PWA** — `static/manifest.json`, `static/sw.js` (servido em
      `/sw.js` via nova rota em `app.py`, necessário pro escopo do
      service worker cobrir o site inteiro) e `static/pwa-register.js`
      incluído em todas as páginas. Ícones 192×192 e 512×512 gerados a
      partir do `apple-touch-icon.png` existente (180×180) — funcionais,
      mas upscaled; uma arte nativa nesses tamanhos ficaria mais nítida
      se algum dia houver tempo pra isso.
- [ ] **19. Navegação por teclado / leitor de tela nas tabelas** — **não
      atacado nesta rodada, por pedido explícito.** Segue pendente:
      revisar `templates/resultado.html` com foco em `tabindex` e
      `aria-label` nas células que hoje comunicam informação só por cor
      (intensidade de fundo).

## Fase 6 — Contas de usuário, times, temporadas e scouting histórico

> Ver `ROADMAP_FASE6.md` para a descrição completa de cada item (contexto,
> arquivos envolvidos, dependências entre itens).

- [x] **20. Login com Google** — `Flask-Login` + `Authlib`, contas
      guardadas em `dados/usuarios.json` por enquanto (`scouting/usuarios.py`
      — ver o comentário no topo do arquivo sobre a migração futura pra
      um banco de verdade, junto com o item 23). Login é opcional: o app
      inteiro continua funcionando sem conta, do jeito que já funcionava.
- [x] **21. Migrar sessão anônima para a conta, no primeiro login** —
      `scouting/sessao.py::adotar_sessao_anonima`; a pasta de dados
      (exports + elenco) passa a ser permanente e atrelada à conta
      (`usr_<id>`) em vez de um UUID por navegador, a partir do login.
- [ ] **22. Magic link por email** — não iniciado (opcional; só faz
      sentido se o login-só-Google se mostrar uma barreira real).
- [x] **23. Banco de dados (Times, Temporadas, Scoutings)** —
      `scouting/models.py` (Flask-SQLAlchemy, SQLite por padrão em
      `dados/app.db`, configurável via `DATABASE_URL`). Tabela
      `scoutings` já existe no schema, mas ainda não é usada (isso é o
      item 30, Bloco D).
- [x] **24. Migrar armazenamento de exports para Time + Temporada** —
      `Temporada.registrar()` guarda qual `export_id` (ver
      `scouting/sessao.py`) pertence a qual Time+rótulo, sem duplicar a
      lógica de salvar/carregar o DataFrame em disco.
- [x] **25. Tela "Meus Times" (CRUD)** — `/times` (listar/criar),
      `/times/<id>` (detalhe), `/times/<id>/renomear`,
      `/times/<id>/excluir`.
- [x] **26. Vincular upload a Time + Temporada** — `/times/<id>/temporadas`
      (POST), separado do `/upload` anônimo original — reenviar o mesmo
      rótulo substitui o export anterior daquela temporada.
- [ ] **27. Comparação Temporada × Temporada** — não iniciado.
- [ ] **28. Generalizar comparação Time × Time** — não iniciado.
- [ ] **29. Scoutings vinculados a temporada vs. observação contínua** —
      não iniciado.
- [ ] **30. Favoritos/notas do `localStorage` pro banco** — não iniciado.
- [ ] **31. Histórico de exports por usuário, sem expiração** — não
      iniciado.
- [ ] **32. Modo demo com dados de exemplo** — não iniciado.
- [ ] **33. Links compartilháveis somente-leitura** — não iniciado.

---

## Itens que ficaram de fora / precisam de decisão sua

- Nenhum pendente no momento — a observação sobre o README
  desatualizado ("tema claro/escuro") foi resolvida junto com o item 11.

---

### Sugestão de próxima sessão

**Item 10 (benchmark)** é o próximo item "produto" que não depende de
fonte externa de dados. Em paralelo, **item 11** falta só a parte de
imagem (GIF/screenshots) — precisa ser feito com o app rodando de
verdade, navegando pela tela.
