# FM Scouting

App Flask para analisar exports do Football Manager (perfil "Volante"):
página inicial de apresentação, rankings por perfil, perfil customizado,
comparador, radar, dispersão, jogadores parecidos, favoritos/notas,
comparação com o elenco do próprio usuário e exportação para CSV.
Instalável como PWA (ver seção "PWA" abaixo).

## Capturas de tela

> 🚧 **Ainda sem GIF/screenshots aqui.** Pra adicionar:
> 1. Rode o app localmente (seção abaixo) e suba um export de exemplo.
> 2. Grave um GIF curto do fluxo upload → resultado → comparador (ex:
>    com [Kap](https://getkap.co/) ou `ffmpeg` a partir de uma gravação
>    de tela) e salve como `docs/demo.gif`.
> 3. Tire 2-3 screenshots das telas principais (dashboard de resultado,
>    comparador, radar) e salve em `docs/`.
> 4. Troque este aviso por `![Demonstração](docs/demo.gif)` e
>    `![Nome da tela](docs/nome-do-arquivo.png)` pra cada screenshot.

## Rodando localmente

```bash
pip install -r requirements.txt
python app.py
```

Acesse http://localhost:5000.

Opcional: defina `FLASK_SECRET_KEY` no ambiente para as sessões de usuário
(ver `scouting/sessao.py`) sobreviverem a um restart do servidor — sem
isso, uma chave aleatória é gerada a cada start e todo mundo precisa
reenviar o arquivo depois de reiniciar.

```bash
export FLASK_SECRET_KEY=$(openssl rand -hex 32)
```

### Login com Google (opcional)

Desde a Fase 6 (`ROADMAP_FASE6.md`), o app tem um botão "Entrar com
Google" — totalmente opcional, o app inteiro funciona sem login, do
jeito que já funcionava antes. A vantagem de logar: os exports e o
elenco enviados passam a ficar numa pasta permanente atrelada à conta,
em vez de uma sessão de navegador (que se perde ao limpar cookies ou
trocar de aparelho) — ver `scouting/sessao.py`.

Para habilitar localmente:

```bash
export GOOGLE_CLIENT_ID=<id do cliente OAuth do Google>
export GOOGLE_CLIENT_SECRET=<segredo do cliente OAuth do Google>
```

Sem essas variáveis, o botão aparece normalmente, mas o clique falha —
ver `DEPLOY.md` para como criar as credenciais OAuth no Google Cloud
Console (necessário antes de divulgar o link publicamente).

### Meus Times (Fase 6, itens 23-26)

Para quem loga, a página **Meus Times** (`/times`) permite organizar
uploads por time (ex: "Botafogo") e temporada (ex: "2025/26") — ver
`scouting/models.py`. Reenviar um export para o mesmo time+rótulo
substitui o export anterior daquela temporada, em vez de duplicar.

Isso usa um banco SQLite (`dados/app.db` por padrão; configurável via
`DATABASE_URL`). Ao rodar `python app.py` localmente, as tabelas são
criadas automaticamente se ainda não existirem. Para outros cenários
(gunicorn, ou depois de mudar algum modelo em `scouting/models.py`),
rode manualmente:

```bash
python scripts/inicializar_banco.py
```

Comparar duas temporadas lado a lado ainda não existe (ver
`ROADMAP_FASE6.md`, item 27) — por enquanto, a página só guarda o
histórico de envios de cada time.

## Rodando os testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes cobrem `scouting/formulas`, `scouting/ranking.py`,
`scouting/parser.py`, `scouting/sessao.py` (testes unitários) e um
conjunto de testes de integração leves que sobem o app Flask de verdade
(`tests/test_app.py`).

## Estrutura

- `app.py` — rotas Flask (home, upload, rankings, AJAX, histórico).
- `scouting/parser.py` — leitura robusta do CSV/XLSX exportado do FM.
- `scouting/formulas/` — cálculo das métricas derivadas (por perfil).
- `scouting/ranking.py` — ranking por perfil, intensidades, similaridade.
- `scouting/sessao.py` — armazenamento de exports por sessão de usuário
  (histórico incluído; a pasta usada passa a ser permanente, atrelada à
  conta, depois do login — ver seção "Login com Google" acima).
- `scouting/models.py` — contas de usuário (login com Google), times e
  temporadas (Fase 6, itens 20 e 23-26), via SQLAlchemy — ver seção
  "Meus Times" acima.
- `scouting/colunas/`, `scouting/perfis/` — configuração de quais colunas
  aparecem em cada aba e os pesos de cada perfil fixo.
- `templates/`, `static/` — front-end (Jinja + JS puro, sem framework).
  Hoje só existe o tema escuro ("Central Tática"); um segundo tema claro
  ("Prancheta de Scout") chegou a existir mas foi removido — ver o
  comentário no topo de `static/style.css`.
- `tests/` — suíte pytest.

## Páginas

- `/` — apresentação do projeto, com um resumo de cada funcionalidade.
- `/enviar` — formulário de upload do export do FM.
- `/elenco` — envia o elenco ("meu time") e compara um jogador escoutado
  com um titular específico ou com a média do elenco.

## PWA

O app pode ser "instalado" (ícone na tela inicial/atalho, abrindo sem a
barra do navegador) em navegadores compatíveis, via
`static/manifest.json` + `static/sw.js` (service worker, servido em
`/sw.js` — ver rota em `app.py`). O service worker só cacheia CSS/JS/
ícones estáticos; páginas e chamadas AJAX sempre passam pela rede, já
que o app depende de sessão/processamento no servidor.

## Deploy e arquitetura

Ver **`DEPLOY.md`** para o guia completo (preparar servidor, gunicorn,
systemd, nginx, HTTPS, checklist antes de divulgar o link). Resumo da
arquitetura de sessão, que é o ponto mais importante a entender antes de
colocar isso no ar para mais de uma pessoa:

Cada visitante recebe uma sessão própria (cookie com ID aleatório), e
cada upload processado fica salvo em disco numa subpasta isolada dessa
sessão (`session_cache/<id-da-sessao>/`) — isso funciona bem com
**múltiplos processos gunicorn no mesmo servidor** (o arquivo em disco é
visível a todos os processos). Se um dia o site crescer para
**múltiplos servidores físicos/virtuais atrás de um load balancer**,
essa solução baseada em disco local deixa de funcionar (cada servidor
teria seu próprio disco) — nesse caso, ou se configuram *sticky
sessions* no load balancer, ou se troca o armazenamento em arquivo por
algo compartilhado (Redis, por exemplo).

## Contribuindo

Veja `CONTRIBUTING.md` para como rodar os testes, convenção de commit e
como adicionar uma métrica nova. O `ROADMAP.md` lista o que já foi feito
e o que ainda está pendente, por fase.

## Licença

MIT — ver `LICENSE`.

