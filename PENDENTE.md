# O que falta para concluir esta rodada

> Continuação de `ROADMAP_FM_SCOUTING.md`. A sessão anterior atacou CI
> (item 16), uma correção de bug e a metade "backend/feedback" do item 8.
> **Esta sessão fechou o restante do item 8 (drag & drop de verdade) e
> implementou o item 6 (paginação) por completo** — ver detalhe abaixo.
> Itens 4/5, 7, 9 (parcial — ver nota) e 10 em diante seguem pendentes.

---

## ✅ Feito nesta sessão (fechamento do item 8 + item 6)

- **Item 8 fechado — drag & drop real**:
  - `static/dropzone.js` (novo): função genérica `configurarDropzone(dropzoneEl, inputEl, labelSpanEl, textoPadrao)`,
    compartilhada por `templates/upload.html` e `templates/elenco.html`.
    Liga `dragover`/`dragenter`/`dragleave`/`dragend`/`drop`, atribui
    `input.files` via `DataTransfer` no drop, e alterna a classe
    `upload-dropzone-ativo` durante o arrasto.
  - As duas templates perderam as funções inline duplicadas
    (`atualizarNomeArquivo` / `atualizarNomeArquivoElenco`) e o
    `onchange` no `<input>`, chamando `configurarDropzone(...)` uma vez
    no carregamento.
  - `static/style.css`: `.upload-dropzone-ativo`, reaproveitando
    `--cor-acento` (mesma cor do hover) com um leve fundo via
    `color-mix()`.

- **Item 6 — paginação nas tabelas de categoria e ranking por perfil**:
  - `static/script.js`: `configurarPaginacao()` (chamada no
    `DOMContentLoaded` junto com `tornarTabelasOrdenaveis()`) identifica
    as tabelas com `tr[data-jogador]` no `tbody` (categoria e ranking por
    perfil — as AJAX como comparador/parecidos não têm essas linhas nesse
    momento e ficam de fora, como previsto) e insere os controles
    "‹ Anterior / Página X de Y (N jogadores) / Próxima ›" logo abaixo de
    cada tabela.
  - `atualizarPaginacao(wrapper)`: conta as linhas sem `linha-oculta`,
    aplica/remove `linha-pagina-oculta` (independente da classe de
    filtro) só nas linhas fora da janela da página atual.
  - Hooks: `aplicarFiltros()` agora reseta cada wrapper paginado pra
    página 1 e recalcula no final; `ordenarTabela()` recalcula a
    paginação da tabela ordenada no final (mesma janela, nova ordem).
  - `static/style.css`: `.linha-pagina-oculta`, `.paginacao-controles`,
    `.paginacao-botao`, `.paginacao-info`, reaproveitando `--cor-borda-forte`,
    `--cor-acento` e `--raio-pequeno` (mesmo padrão visual do botão
    "Limpar filtros").
  - Tamanho de página fixo em 50 (`PAGINACAO_TAMANHO_PAGINA`).
  - Suíte `pytest` seguiu passando 116/116 (mudança é 100% front-end,
    como previsto — não tocou em `app.py` nem `scouting/`).

**Nota sobre o item 9**: ao abrir o zip enviado, `templates/elenco.html`
e a rota `/elenco` já existiam prontos (upload de elenco, comparador
jogador-vs-elenco, `elenco.js`) — ou seja, o item 9 do roadmap parece já
ter sido implementado em algum momento não documentado no `PENDENTE.md`
anterior. Vale conferir se `scouting/sessao.py` já tem o campo `tipo`
mencionado no roadmap, e atualizar o roadmap principal para refletir
isso.

---

## ✅ Feito nesta sessão

1. **CI com GitHub Actions (item 16)** — `.github/workflows/tests.yml`,
   roda `pytest` a cada push/PR na `main` e via `workflow_dispatch`.

2. **Bug de isolamento de testes corrigido (fora do roadmap, achado no
   caminho)** — `TestRateLimitUpload` esgotava o rate limiter e
   "vazava" isso para `TestElenco`, quebrando 2 testes de forma
   determinística sempre que a suíte rodava inteira (o que aconteceria
   a cada push, com o CI novo). Causa: Flask-Limiter 3.8 lê
   `RATELIMIT_ENABLED` de `app.config` só uma vez, dentro de
   `init_app()` — mudar `app.config` depois disso não tem efeito
   nenhum; quem precisa mudar é o atributo `limiter.enabled`
   diretamente. Corrigido em `tests/test_app.py` (fixtures `client` e
   `client_com_limite_ativo`). Suíte agora passa 116/116 de forma
   estável, rodando repetidas vezes.

3. **Item 8 (upload mais amigável) — só a metade "backend/feedback"**:
   - `app.py`: a rota `/upload` agora cronometra o bloco de parsing +
     cálculo de métricas (`time.perf_counter()`), e captura
     `num_linhas_lidas` (logo após `carregar_arquivo`) e
     `num_jogadores_validos` (após `calcular_volantes`) — hoje os dois
     números batem, mas ficam calculados em pontos diferentes de
     propósito: se um parser mais rigoroso passar a descartar linhas
     inválidas no futuro, os números já vão divergir sem precisar
     mexer nesse trecho de novo.
   - `templates/resultado.html`: banner dispensável no topo do
     dashboard mostrando nome do arquivo, formato (CSV/XLSX), linhas
     lidas, jogadores válidos e tempo de processamento.
   - `static/style.css`: estilo do banner (`.feedback-upload`),
     seguindo as variáveis de cor do tema existente (funciona nos dois
     temas, claro e escuro).

---

## 🔴 Falta fazer para fechar o item 8 por completo

O que falta é a metade "drag & drop de verdade", que estava mapeada mas
não foi implementada ainda:

- **`templates/upload.html`** e **`templates/elenco.html`**: hoje o
  `upload-dropzone` é só um `<label>` estilizado sobre um
  `<input type="file">` — clique funciona, mas arrastar um arquivo por
  cima não faz nada. Falta:
  - Um `static/dropzone.js` (compartilhado pelas duas páginas, que hoje
    têm cada uma sua função `atualizarNomeArquivo*` num `<script>`
    inline) com uma função genérica tipo
    `configurarDropzone(dropzoneEl, inputEl, labelSpanEl, textoPadrao)`
    escutando `dragover`/`dragleave`/`drop`, atribuindo
    `input.files` via `DataTransfer` no `drop`, e alternando uma classe
    `upload-dropzone-ativo` durante o arrasto (com o respectivo estilo
    em `static/style.css`, reaproveitando `--cor-acento`).
  - Trocar as chamadas `onchange="atualizarNomeArquivo(this)"` /
    `atualizarNomeArquivoElenco(this)` para usar essa função
    compartilhada, sem duplicar lógica entre as duas páginas.
  - Incluir `<script src="{{ url_for('static', filename='dropzone.js') }}"></script>`
    nas duas templates.

Não é um trabalho grande — a parte que dava mais trabalho (a
cronometragem e o feedback numérico no backend) já está pronta; falta
só a interação de arrastar-e-soltar em si.

---

## 🔴 Item 6 — Paginação/virtualização (não iniciado)

Ainda não comecei este item. Plano (mapeado, mas não implementado):

- **`static/script.js`**: nova função `configurarPaginacao()`, chamada
  no `DOMContentLoaded` junto com `tornarTabelasOrdenaveis()`. Para
  cada `.tabela-wrapper table` que tenha `tr[data-jogador]` no `tbody`
  (as tabelas de categoria e de ranking por perfil, que são as que
  recebem a base inteira — as tabelas AJAX como comparador/parecidos já
  são naturalmente pequenas):
  - Tamanho de página fixo (ex: 50 linhas), guardado em
    `wrapper.dataset.paginaAtual`.
  - `atualizarPaginacao(wrapper)`: conta as linhas que **passaram nos
    filtros** (sem a classe `linha-oculta`, que é a classe que
    `aplicarFiltros()` já usa hoje), calcula o total de páginas, e
    aplica/remove uma segunda classe (`linha-pagina-oculta`, também
    `display:none` no CSS) só nas linhas fora do intervalo da página
    atual — sem interferir na classe de filtro.
  - Controles "‹ Anterior / Página X de Y (N jogadores) / Próxima ›"
    inseridos logo abaixo de cada tabela.
- **Hooks necessários** (para não deixar a paginação dessincronizada):
  - No fim de `aplicarFiltros()`: resetar cada wrapper pra página 1 e
    chamar `atualizarPaginacao()` de novo (o total de linhas visíveis
    muda a cada filtro).
  - No fim de `ordenarTabela()`: chamar `atualizarPaginacao(tabela.closest('.tabela-wrapper'))`
    de novo (a ordem mudou, então a "janela" da página atual precisa
    ser recalculada sobre a nova ordem).
- **CSS**: `.linha-pagina-oculta { display: none; }` e o estilo dos
  controles de paginação (reaproveitando `--cor-borda`, `--cor-acento`,
  etc., mesmo padrão visual dos botões de filtro).

Não precisa mexer em `app.py` nem em `scouting/`: é 100% front-end,
porque os filtros já são client-side (dados inteiros vêm no HTML) — a
paginação só decide quais linhas, das já filtradas, ficam visíveis por
vez.

---

## Itens do roadmap original ainda não iniciados

Sem mudança desde a última avaliação — continuam pendentes:

- **Fase 2**: item 4/5 (cache do ranking com Flask-Caching), item 7
  (upload assíncrono).
- **Fase 3**: item 10 (benchmark comparativo: média/percentis da
  liga).
- **Fase 4**: `LICENSE`, `CONTRIBUTING.md`, GIF/screenshots no README.
- **Fase 5**: meta tags OpenGraph, PWA (`manifest.json` + service
  worker, ícones já prontos em `static/`), `aria-label`/`tabindex` nas
  tabelas.

---

### Sugestão de próxima sessão

Fechar o drag & drop (rápido, o backend já está pronto) → implementar
a paginação (item 6, o mais trabalhoso do que falta aqui) → seguir para
o item 10 (benchmark), que é o próximo item "produto" com dados que já
temos disponíveis sem depender de fonte externa.
