# Guia de Deploy — FM Scouting

Este guia assume um servidor Linux (Ubuntu/Debian) com Python 3.11+ e
acesso root/sudo. Cobre o caminho mais comum e realista para este projeto:
**um servidor, múltiplos workers**, atrás de um proxy reverso com HTTPS.

---

## 0. Antes de tudo: o que mudou para isso ser seguro

Até pouco tempo atrás, o app guardava os dados de cada upload numa
variável Python global (`ultimo_df`), compartilhada por **todo mundo**
usando o site ao mesmo tempo. Isso foi corrigido (ver `scouting/sessao.py`):
agora cada visitante tem uma sessão própria (um cookie com um ID
aleatório), e cada upload processado fica guardado em disco, isolado numa
pasta própria daquela sessão (`session_cache/<id-da-sessao>/`) — o que
também permite manter, por sessão, o elenco enviado pelo usuário como
base comparativa (ver GET /elenco), não só "o último upload".

Isso resolve o cenário realista de deploy — **um servidor, vários
processos `gunicorn`** — porque o arquivo em disco é visível para todos os
processos, ao contrário de uma variável em memória. Se um dia este site
crescer para **múltiplos servidores físicos/virtuais atrás de um load
balancer**, essa solução baseada em arquivo local deixa de funcionar (cada
servidor teria seu próprio disco) — nesse caso, ou se configura "sticky
sessions" no load balancer (mesma pessoa sempre cai no mesmo servidor), ou
se troca o armazenamento em arquivo por algo compartilhado (Redis, por
exemplo — a interface de `scouting/sessao.py` foi pensada pra isso ser uma
troca pequena, não uma reescrita).

---

## 1. Preparar o servidor

```bash
sudo apt update
sudo apt install python3-venv python3-pip nginx -y

sudo mkdir -p /var/www/fm-scouting
sudo chown $USER:$USER /var/www/fm-scouting
```

Envie os arquivos do projeto para `/var/www/fm-scouting` (git clone, scp,
rsync — o que preferir).

## 2. Ambiente virtual e dependências

```bash
cd /var/www/fm-scouting
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Variáveis de ambiente

Crie um arquivo `.env` (ou defina direto no systemd, seção 5) com:

```bash
FLASK_SECRET_KEY=<gere um valor aleatório — comando abaixo>
FLASK_DEBUG=0
GOOGLE_CLIENT_ID=<id do cliente OAuth do Google>
GOOGLE_CLIENT_SECRET=<segredo do cliente OAuth do Google>
DATABASE_URL=sqlite:////var/www/fm-scouting/dados/app.db
```

Gerar uma `FLASK_SECRET_KEY` forte:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Sem essa variável**, o app cai num fallback local: gera uma chave e a
salva em `.flask_secret_key` (na raiz do projeto, fora do git) na primeira
vez que roda, reaproveitando o mesmo valor nas próximas execuções — isso
evita perder sessões (elenco enviado em `/elenco`, export em andamento
etc.) a cada `python app.py`/reload do modo debug. **Em produção, ainda
assim defina `FLASK_SECRET_KEY` explicitamente**: com múltiplos workers do
gunicorn (`-w 4`, seção 5), cada processo importa `app.py`
independentemente, e na primeiríssima vez que o arquivo `.flask_secret_key`
ainda não existe, workers que sobem ao mesmo tempo podem competir para
criá-lo e acabar com chaves diferentes entre si — com a variável de
ambiente definida, esse fallback nem entra em ação, e todos os workers
usam o mesmo valor com certeza.

### Login com Google (opcional, mas recomendado em produção)

O botão "Entrar com Google" (Fase 6, item 20 do `ROADMAP_FASE6.md`) usa
OAuth 2.0. Sem `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` configuradas, o
resto do app funciona normalmente — só o clique no botão falha. Pra
habilitar:

1. [Google Cloud Console](https://console.cloud.google.com/) → **APIs e
   serviços → Credenciais → Criar credenciais → ID do cliente OAuth**
   (tipo "Aplicativo da Web").
2. Em **URIs de redirecionamento autorizados**, adicione
   `https://<seu-dominio>/auth/callback` — precisa ser HTTPS (ver seção
   4 abaixo) e bater exatamente com o domínio final, senão o Google
   recusa o callback.
3. Copie o **ID do cliente** e o **Segredo do cliente** gerados para as
   variáveis `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` acima.

### Banco de dados (contas, Times, Temporadas — Fase 6)

`DATABASE_URL` é opcional — sem ela, o app usa
`sqlite:///dados/app.db` (relativo à pasta onde o processo roda). Em
produção, defina um caminho absoluto (exemplo acima) para não depender
de qual diretório o gunicorn foi iniciado.

Depois de configurar as variáveis (ou aceitar o padrão), crie as tabelas
uma vez, manualmente — `db.create_all()` não roda sozinho fora de
`python app.py` (ver comentário em `app.py`):

```bash
python scripts/inicializar_banco.py
```

Rode esse mesmo comando de novo sempre que adicionar/mudar um modelo em
`scouting/models.py` — o projeto ainda não usa uma ferramenta de
migração de schema (tipo Alembic), então `create_all()` só cria tabelas
que ainda não existem, não altera colunas de tabelas já existentes.

## 4. Pastas graváveis

O app precisa conseguir escrever em duas pastas (criadas automaticamente
no primeiro request, mas é mais seguro garantir antes):

```bash
mkdir -p uploads session_cache
```

- `uploads/` — recebe o arquivo temporariamente durante o processamento e
  é apagado logo em seguida (ver `app.py`, bloco `finally` da rota
  `/upload`). Não deveria acumular nada em uso normal.
- `session_cache/` — um `.pkl` por export + um `metadata.json`, dentro de
  uma subpasta por sessão ativa. Cada sessão guarda no máximo
  `MAX_EXPORTS_POR_SESSAO` (10) exports — o mais antigo é apagado
  automaticamente ao ultrapassar o limite (ver `scouting/sessao.py`). Não
  há expiração por tempo ainda; se o servidor acumular muitas sessões
  distintas ao longo do tempo, considere uma limpeza agendada (cron)
  apagando subpastas de `session_cache/` mais antigas que X dias.

## 5. Rodar com gunicorn

**Nunca** use `python app.py` (que chama `app.run()`) em produção — é o
servidor de desenvolvimento do próprio Flask, sem gestão de processos,
sem restart em caso de erro, e não pensado para lidar com carga real.

Teste manualmente primeiro:

```bash
source venv/bin/activate
export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

- `-w 4` = 4 processos worker. Regra prática: `(2 × números de CPU) + 1`.
  Como a app faz operações em memória com pandas (sem esperar banco de
  dados externo), não precisa de dezenas de workers — comece com 4 e
  ajuste observando o uso de CPU/memória real.
- `-b 127.0.0.1:8000` = escuta só localmente; o nginx (seção 7) expõe pro
  mundo. Não exponha a porta do gunicorn diretamente na internet.

Se abrir `http://127.0.0.1:8000` no próprio servidor e funcionar, prossiga
para deixar isso permanente com systemd.

## 6. systemd (mantém o app rodando e reinicia sozinho)

Crie `/etc/systemd/system/fm-scouting.service`:

```ini
[Unit]
Description=FM Scouting (gunicorn)
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/fm-scouting
Environment="FLASK_SECRET_KEY=troque-por-um-valor-gerado-com-secrets-token-hex"
Environment="FLASK_DEBUG=0"
ExecStart=/var/www/fm-scouting/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Ajuste o dono das pastas para o usuário do serviço (`www-data` no
exemplo), e então:

```bash
sudo chown -R www-data:www-data /var/www/fm-scouting
sudo systemctl daemon-reload
sudo systemctl enable fm-scouting
sudo systemctl start fm-scouting
sudo systemctl status fm-scouting   # confirma que subiu sem erro
```

## 7. nginx como proxy reverso

Crie `/etc/nginx/sites-available/fm-scouting`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    client_max_body_size 16M;  # um pouco acima do limite de 15MB do app

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/fm-scouting /etc/nginx/sites-enabled/
sudo nginx -t   # valida a config antes de aplicar
sudo systemctl reload nginx
```

## 8. HTTPS (obrigatório se pessoas fora da sua rede vão acessar)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d seu-dominio.com
```

O certbot edita a config do nginx automaticamente e configura renovação
automática do certificado.

---

## Checklist antes de divulgar o link para outras pessoas

- [ ] `FLASK_SECRET_KEY` definida via variável de ambiente (valor fixo, não gerado a cada restart)
- [ ] `FLASK_DEBUG` **não** está setada como `1` (o padrão já é `0`, mas confirme)
- [ ] `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` definidas, com a URI de redirecionamento `https://<seu-dominio>/auth/callback` cadastrada no Google Cloud Console (ver seção 3 acima) — sem isso o app funciona, mas o botão "Entrar com Google" falha
- [ ] `python scripts/inicializar_banco.py` rodado ao menos uma vez (contas, Times, Temporadas — ver seção 3 acima), e de novo após qualquer mudança em `scouting/models.py`
- [ ] Rodando via `gunicorn` + systemd, não `python app.py`
- [ ] nginx configurado com `client_max_body_size` compatível com o limite de upload
- [ ] HTTPS ativo (certbot)
- [ ] `uploads/`, `session_cache/` e `dados/` (contas de usuário) graváveis pelo usuário do serviço
- [ ] Rodou `pytest` (ver README.md) antes do deploy
- [ ] Testou o fluxo completo (home → upload → tabelas → comparador →
      jogadores parecidos → histórico → comparação de exports) através do
      domínio público, não só localmente
- [ ] Testou o login com Google de ponta a ponta pelo domínio público (o
      callback OAuth não funciona em `localhost` sem configuração extra)

## Se o uso crescer bastante

- **Muitas pessoas ao mesmo tempo, mesmo servidor:** aumente `-w` no
  gunicorn gradualmente, observando CPU/memória.
- **Mais de um servidor físico/virtual:** troque `session_cache` por Redis
  (ou configure sticky sessions no load balancer) — ver nota na seção 0.
- **Uploads muito grandes ou muito frequentes:** considere rate limiting
  (ex: `flask-limiter`) na rota `/upload`.
