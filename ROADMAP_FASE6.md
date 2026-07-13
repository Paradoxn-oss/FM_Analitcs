# Fase 6 — Contas de usuário, times, temporadas e scouting histórico

> **Status**: Bloco A (itens 20 e 21) e Bloco B (itens 23-26) implementados.
> Ver `CHANGELOG_SESSAO.md` (ou o histórico de commits) para o detalhe do
> que foi feito. Blocos C, D e E ainda não iniciados — este arquivo
> continua servindo de prompt pra próxima sessão, a partir daqui.
>
> Nota sobre "viewer" de uma temporada específica: o item 26 guarda qual
> export pertence a qual Time+rótulo, mas ainda não existe uma rota que
> RE-renderize o dashboard completo (resultado.html) a partir de um
> export_id armazenado — isso ficou deliberadamente para o item 27
> (comparação entre temporadas), que é o primeiro lugar onde isso
> realmente precisa existir, em vez de duplicar a lógica de
> `/upload` (que hoje só sabe montar o dashboard a partir de um arquivo
> recém-enviado) sem um caso de uso concreto ainda puxando isso.

> Como usar este arquivo: mesma lógica do `ROADMAP_FM_SCOUTING.md` — cole a
> seção que quiser atacar numa sessão nova (aqui ou no Claude Code, com o
> repo aberto) e peça pra implementar item por item. Diferente das fases
> 1-5, esta é uma mudança estrutural (adiciona banco de dados e login de
> verdade), então os itens têm mais dependência entre si — a ordem sugerida
> no fim importa mais aqui do que nas fases anteriores.

## Contexto / por que essa fase existe

Hoje (ver `scouting/sessao.py`) os dados vivem por **sessão anônima de
navegador**: um cookie com ID aleatório, e os exports processados salvos
em `session_cache/<id-da-sessao>/*.pkl`, com um limite de
`MAX_EXPORTS_POR_SESSAO` e limpeza por idade
(`scripts/limpar_sessoes_antigas.py`). Isso funciona bem pra "processar um
arquivo e ver o resultado", mas não guarda nada de forma confiável: some
se a pessoa limpar cookies, trocar de aparelho, ou a sessão expirar — e
não existe hoje nenhum conceito de "Time" ou "Temporada" no modelo de
dados, só "o último export enviado" e um histórico raso de uploads da
mesma sessão.

O objetivo desta fase: introduzir conta de usuário persistente (login) +
um modelo de dados que entenda **Time** (ex: "Botafogo", "meu save da
Champions") e **Temporada** (cada upload vinculado a um time E a uma
temporada daquele time), permitindo comparar a evolução de um time entre
temporadas e manter os scoutings (favoritos + notas, hoje só no
`localStorage` do navegador) presos à conta, não ao aparelho.

---

## A. Autenticação

### 20. Login social com Google (`Flask-Login` + `Authlib`)
Adicionar `Flask-Login` (gerencia sessão do usuário logado) e `Authlib`
(fluxo OAuth do Google). Fluxo: botão "Entrar com Google" → callback em
`/auth/callback` → cria (ou recupera) o usuário no banco pelo `sub` do
Google → `login_user()`. Variáveis de ambiente novas:
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (mesma lógica do
`FLASK_SECRET_KEY` já existente — ver `README.md`, seção "Rodando
localmente").
⚠️ **Pré-requisito de deploy**: o Google exige uma URL de callback
registrada e HTTPS em produção — ver `DEPLOY.md` (a seção de HTTPS já
existente cobre isso, mas o item de checklist "antes de divulgar o link"
precisa incluir registrar o client OAuth com o domínio final).

### 21. Migrar sessão anônima existente para a conta, no primeiro login
Quando alguém que já usava o site sem login loga pela primeira vez, a
sessão anônima atual (`session_cache/<id-da-sessao>/`) não deve ser
jogada fora — vincular esses exports órfãos à conta recém-criada
(perguntar "quer manter os dados que você já tinha enviado?" é mais
amigável que simplesmente perder tudo no primeiro login).

### 22. (opcional) Magic link por email como alternativa ao Google
Pra quem não quer/não tem conta Google: campo de email → link de acesso
de uso único, sem senha. Menor prioridade que os itens acima — só faz
sentido se o login-only-Google se mostrar uma barreira real de adoção.

---

## B. Banco de dados e modelo (Times, Temporadas, Scoutings)

### 23. Introduzir banco via `Flask-SQLAlchemy` (SQLite pra começar)
Tabelas iniciais:
- `usuarios` (id, google_sub, email, nome, criado_em)
- `times` (id, usuario_id, nome, criado_em)
- `temporadas` (id, time_id, rotulo — ex: "2025/26", enviado_em,
  num_jogadores, caminho_do_export ou dados serializados)
- `scoutings` (id, usuario_id, jogador, time_id nullable, temporada_id
  nullable, favorito bool, nota_texto, criado_em, atualizado_em)

SQLite é suficiente pra começar (arquivo único, sem servidor de banco
separado — combina com o mesmo espírito de baixa infraestrutura do
`session_cache/` atual) e migra pra Postgres depois sem reescrever o
modelo, se o site crescer.

### 24. Migrar o armazenamento de exports para Time + Temporada
Hoje `scouting/sessao.py` (`salvar_export`, `carregar_export`,
`listar_exports`) trabalha só com "sessão". Generalizar pra receber
`(usuario_id, time_id, temporada_id)` em vez de só `sessao` — o
`.pkl` do DataFrame calculado pode continuar em disco (não precisa virar
BLOB no banco), só a chave de organização muda. `PADRAO_EXPORT_ID` e a
validação de path traversal (`export_id_valido`) continuam do jeito que
estão, só trocando o que compõe o caminho da pasta.

### 25. Tela "Meus Times" (CRUD)
Nova rota/tela pra criar, renomear e excluir times. Ponto de entrada
natural depois do login — em vez de cair direto em "/enviar", o usuário
logado vê a lista dos times que já tem, com botão de criar um novo.

### 26. Vincular upload a Time + Temporada específicos
A rota `/upload` (`app.py`) passa a pedir (ou perguntar, se for o
primeiro upload daquele time) a qual time e temporada aquele export
pertence, em vez de só "substituir o último export da sessão".

---

## C. Comparação entre temporadas e times

### 27. Comparação Temporada × Temporada do mesmo Time
Tela nova: escolher duas temporadas do mesmo Time e ver a evolução
jogador a jogador (mesmo jogador, métricas lado a lado entre as duas
temporadas) — é o caso de uso que a conversa que originou esta fase
apontou como o que mais falta hoje. Reaproveita bastante lógica de
`scouting/ranking.py` (comparação de métricas já existe pro comparador
atual) e do JS existente do comparador (`static/script.js`), só trocando
a fonte dos dois "lados" da comparação: em vez de "jogador A vs jogador
B do mesmo export", vira "mesmo jogador em dois exports diferentes".

### 28. Generalizar a comparação Time × Time
Hoje só existe comparação jogador-escoutado × elenco (`/elenco/comparar`,
`scouting/ranking.py::comparar_metricas_vs_elenco`). Generalizar pra
comparar dois Times quaisquer do usuário (não só "elenco vs scouting"),
reaproveitando a mesma função de comparação de métricas.

### 29. Scoutings vinculados a uma temporada vs. "observação contínua"
Ao favoritar/anotar um jogador (hoje: `favoritos`/notas no
`localStorage`, ver `obterFavoritos()` em `static/script.js`), permitir
marcar se aquele scouting é específico de uma temporada (ex: "observei
esse jogador na janela de 2026/27") ou uma observação solta que não
precisa estar presa a nenhuma temporada.

---

## D. Migrar recursos hoje soltos pro modelo novo

### 30. Favoritos e notas: do `localStorage` pro banco
Hoje vivem só no navegador (não sincronizam entre aparelhos, se perdem
se limpar dados do navegador). Vira a tabela `scoutings` do item 23,
amarrada ao usuário — resolve exatamente a limitação que motivou essa
fase.

### 31. Histórico de exports por usuário, sem expiração automática
O histórico de uploads (hoje por sessão anônima, com
`MAX_EXPORTS_POR_SESSAO` e limpeza por idade via
`scripts/limpar_sessoes_antigas.py`) passa a ser por usuário logado —
sem prazo de expiração (é dado de conta, não cache de sessão temporária).
O script de limpeza por idade continua fazendo sentido só pra sessões
**anônimas** (quem ainda não logou).

---

## E. Extras de produto (site público)

### 32. Modo demo com dados de exemplo
Botão na home ("ver com dados de exemplo") que mostra o dashboard
completo sem precisar de upload nem login — reduz a fricção de alguém
desconhecido decidir se vale a pena criar conta.

### 33. Links compartilháveis somente-leitura
Gerar um link tipo `/compartilhado/<hash>` que mostra um ranking ou
comparação específica sem quem recebe o link precisar de conta — bom
gancho de crescimento orgânico pra um site público.

---

## Dependências novas (`requirements.txt`)

```
Flask-Login
Flask-SQLAlchemy
Authlib
```

## Sugestão de ordem de ataque

**Itens 20 e 23 primeiro e juntos** (login + banco têm que nascer
integrados — não faz sentido montar o banco de Times/Temporadas antes de
ter um `usuario_id` de verdade pra amarrar nas tabelas) → **21** (migração
da sessão anônima, pra não perder dado de quem já testava o site) → **24,
25, 26** (Time/Temporada viram parte do fluxo de upload) → **27, 28, 29**
(as telas de comparação que são o motivo original desta fase) → **30, 31**
(mover favoritos/histórico pro modelo novo) → **32, 33** (extras de
crescimento, só depois do núcleo funcionando) → **22** (magic link, só se
o Google se mostrar insuficiente como única opção de login).

⚠️ Diferente das fases 1-5, esta fase muda a arquitetura de dados do
projeto (introduz banco onde hoje só tem arquivo + cookie). Vale rodar os
itens 20+23 numa branch separada e confirmar que a suíte `pytest` inteira
continua passando antes de emendar os itens seguintes — a mudança de
"sessão" pra "usuário" toca em `scouting/sessao.py`, que é usado por
praticamente toda rota AJAX existente (perfil customizado, jogadores
parecidos, melhor perfil, elenco).
