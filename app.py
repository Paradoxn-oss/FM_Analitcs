"""
Aplicação Flask do FM Scouting.

Fluxo geral:
1. GET  "/"                    -> página inicial de apresentação do projeto
                                   (templates/home.html).
2. GET  "/enviar"               -> formulário de upload (templates/upload.html)
3. POST "/upload"              -> processa o arquivo e renderiza o dashboard
                                   completo (templates/resultado.html): tabelas
                                   por categoria, rankings por perfil, gráfico
                                   de dispersão, comparador de jogadores,
                                   perfil customizado e jogadores parecidos.
4. POST "/perfil-customizado"  -> (AJAX) recalcula um ranking com pesos
                                   escolhidos livremente pelo usuário na tela.
5. POST "/jogadores-parecidos" -> (AJAX) busca os jogadores estatisticamente
                                   mais parecidos com um jogador de referência.
6. POST "/melhor-perfil"       -> (AJAX) ranking reverso: a nota de UM
                                   jogador em todos os perfis fixos.
7. GET  "/elenco"               -> tela do "meu time" (templates/elenco.html):
                                   upload do elenco do usuário e, se já
                                   houver um export escoutado nesta sessão,
                                   o formulário de comparação jogador
                                   escoutado x elenco.
8. POST "/elenco/upload"        -> processa o upload do elenco (mesmo
                                   parser/fórmulas do upload principal) e
                                   salva como o elenco atual da sessão.
9. POST "/elenco/comparar"      -> (AJAX) compara um jogador escoutado com
                                   o elenco: contra um jogador específico
                                   ou contra a média do elenco. A "Nota do
                                   Perfil" do candidato é recalculada com o
                                   elenco como grupo de referência, em vez
                                   dos demais jogadores escoutados.
10. GET "/login"                -> inicia o login com Google (Fase 6, item
                                   20 do ROADMAP_FASE6.md). Opcional: o app
                                   inteiro funciona sem login, do jeito que
                                   já funcionava antes.
11. GET "/auth/callback"        -> volta do consentimento do Google, cria
                                   ou recupera a conta e loga o usuário.
12. GET "/logout"               -> desloga (não apaga nenhum dado salvo).
"""

import os
import secrets
import time
import uuid
from datetime import datetime

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename

# carregar_arquivo: lê o CSV/XLSX exportado do FM e devolve um DataFrame bruto
# extensao_permitida: valida a extensão do arquivo antes de salvar em disco
# ArquivoInvalidoError: erro de dados malformados (encoding, separador, CSV
# vazio etc.)
from scouting.parser import ArquivoInvalidoError, carregar_arquivo, extensao_permitida

# calcular_volantes: transforma as colunas brutas do FM nas métricas
# calculadas (por 90 min, percentuais etc.) específicas do perfil "Volante"
from scouting.formulas.volantes import calcular_volantes
from scouting.formulas.util import ColunaAusenteError

# COLUNAS_VOLANTES: define quais colunas aparecem em cada aba da tela de
# resultado
# PERFIS_VOLANTES: define os pesos de cada métrica para calcular a "Nota do
# Perfil"
from scouting.colunas.volantes import COLUNAS_VOLANTES
from scouting.perfis.volantes import PERFIS_VOLANTES

# calcular_ranking: normaliza as métricas (0 a 1) e pondera pelos pesos do
# perfil (usado tanto pelos perfis fixos quanto pelo perfil customizado)
# calcular_intensidades: gera o valor de 0 a 1 usado para colorir as células
# calcular_similares: acha os jogadores mais parecidos com um jogador dado
from scouting.ranking import (
    ColunaAusenteError as RankingColunaAusenteError,
    calcular_intensidades,
    calcular_notas_vs_elenco,
    calcular_ranking,
    calcular_similares,
    comparar_metricas_vs_elenco,
)

# Armazenamento de DataFrames por sessão de usuário (ver docstring do
# módulo para o motivo: evita que o upload de uma pessoa "substitua" os
# dados que outra pessoa está analisando, quando o app é usado por mais de
# um usuário ao mesmo tempo).
from scouting.sessao import (
    CHAVE_USUARIO_ID,
    adotar_sessao_anonima,
    carregar_df_atual,
    carregar_elenco,
    elenco_metadata,
    remover_elenco,
    salvar_elenco,
    salvar_export,
)

# Contas de usuário, times e temporadas (Fase 6, itens 20 e 23-26).
from scouting.models import db, Temporada, Time, Usuario

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

# Necessário para o cookie de sessão (usado por scouting/sessao.py para
# isolar os dados de cada usuário, inclusive o elenco em /elenco) ser
# assinado e não-falsificável.
#
# Em produção, defina a variável de ambiente FLASK_SECRET_KEY com um valor
# fixo (ex: `openssl rand -hex 32`).
#
# Quando essa variável NÃO está definida (uso pessoal/local, sem configurar
# nada), a chave é gerada uma vez e persistida em disco (ARQUIVO_SECRET_KEY
# abaixo), em vez de sorteada de novo a cada reinício do processo. Isso
# evita um bug real: como o cookie de sessão guarda o ID da sessão (usado
# por scouting/sessao.py para achar o elenco.pkl salvo em /elenco/upload),
# toda vez que a chave mudava — o que acontecia a cada `python app.py`,
# inclusive a cada reload automático do modo debug — os cookies antigos
# ficavam inválidos e o app perdia a referência ao elenco (e ao export)
# já enviados, como se o usuário nunca tivesse enviado nada.
ARQUIVO_SECRET_KEY = os.path.join(os.path.dirname(__file__), ".flask_secret_key")


def _obter_secret_key():
    chave_env = os.environ.get("FLASK_SECRET_KEY")
    if chave_env:
        return chave_env

    if os.path.exists(ARQUIVO_SECRET_KEY):
        with open(ARQUIVO_SECRET_KEY, encoding="utf-8") as arquivo:
            chave_salva = arquivo.read().strip()
        if chave_salva:
            return chave_salva

    chave_nova = secrets.token_hex(32)
    with open(ARQUIVO_SECRET_KEY, "w", encoding="utf-8") as arquivo:
        arquivo.write(chave_nova)
    return chave_nova


app.secret_key = _obter_secret_key()

# Limite de tamanho de upload: 15 MB. Sem isso, qualquer arquivo (grande
# demais ou malicioso) podia ser enviado sem restrição alguma.
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

# Garante que a pasta de uploads existe antes do primeiro request (evita
# erro na primeira execução em um ambiente novo/limpo).
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Rate limiting: evita que uma única origem consiga sobrecarregar a CPU
# do plano gratuito do PythonAnywhere só de martelar POST /upload (cada
# upload processa um DataFrame inteiro — parsing + cálculo de fórmulas —
# então é a rota mais cara do app). O limite de fato é aplicado só na
# rota /upload (ver @limiter.limit abaixo); default_limits=[] deixa as
# demais rotas sem limite algum por padrão.
#
# Armazenamento em memória (padrão do Flask-Limiter sem STORAGE_URI
# configurada) é suficiente aqui: o app roda como um único processo
# gunicorn no PythonAnywhere, sem múltiplos workers dividindo o mesmo
# limite. Se isso mudar no futuro (múltiplos workers/processos), configure
# STORAGE_URI para um Redis compartilhado.
#
# RATELIMIT_ENABLED pode ser desligado explicitamente (ex: nos testes,
# ver tests/conftest.py) sem precisar remover o decorator da rota.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
)

# ---------------------------------------------------------------------
# Banco de dados: contas, times e temporadas (Fase 6, item 23).
#
# Caminho ABSOLUTO calculado a partir do diretório de trabalho atual (no
# import deste módulo) — de propósito, para não depender da resolução
# implícita de caminhos relativos do Flask-SQLAlchemy (que usa
# app.instance_path, uma pasta diferente de onde session_cache/ e
# uploads/ já vivem). Mantém o banco como mais um "vizinho" dessas pastas
# na raiz do projeto, em vez de escondido dentro de instance/.
#
# Em produção, defina DATABASE_URL (ex: pra migrar pra Postgres depois
# sem mudar nenhum modelo — ver scouting/models.py). Nos testes, essa
# variável é forçada para "sqlite:///:memory:" antes de qualquer coisa
# importar este módulo (ver tests/conftest.py).
_CAMINHO_BANCO_PADRAO = os.path.join(os.getcwd(), "dados", "app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{_CAMINHO_BANCO_PADRAO}"
)
db.init_app(app)


# ---------------------------------------------------------------------
# Login com Google (Fase 6, item 20 do ROADMAP_FASE6.md).
#
# Login é OPCIONAL em todo o app: quem não loga continua usando tudo
# normalmente, do jeito que já funcionava (sessão anônima por navegador,
# ver scouting/sessao.py). A conta só existe pra quem quer que os dados
# (exports enviados, elenco e agora Times/Temporadas — itens 25/26)
# sobrevivam a trocar de navegador/aparelho — ver adotar_sessao_anonima()
# em scouting/sessao.py.
#
# Em produção, defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no ambiente
# (Google Cloud Console -> Credenciais -> ID do cliente OAuth 2.0; a URL
# de redirecionamento autorizada precisa ser
# "https://<seu-dominio>/auth/callback" — ver DEPLOY.md). Sem essas
# variáveis definidas, o botão "Entrar com Google" aparece normalmente,
# mas o clique falha — mesmo espírito do FLASK_SECRET_KEY acima: opcional
# para rodar localmente, obrigatório antes de divulgar o link de verdade.
app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")

oauth = OAuth(app)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

login_manager = LoginManager()
login_manager.init_app(app)
# Com login_view configurada, @login_required (ver rotas /times abaixo)
# redireciona automaticamente pra /login (com ?next=... de volta pra cá)
# em vez de devolver um 401 cru — bem mais amigável num site público.
login_manager.login_view = "login"


@login_manager.user_loader
def carregar_usuario(usuario_id):
    """Chamado pelo Flask-Login em toda requisição de alguém já logado,
    pra reconstruir o objeto Usuario a partir do ID salvo no cookie de
    sessão. Devolver None (usuário não encontrado) faz o Flask-Login
    tratar a requisição como anônima, sem erro."""
    return db.session.get(Usuario, int(usuario_id))




# Colunas cujo valor bruto é uma proporção (0.0 a 1.0) e deve ser exibido
# como porcentagem multiplicada por 100 (ex: 0.833 -> "83.3%").
PERCENTUAIS_PROPORCAO = {
    "% de vezes que foi eleito o Homem do Jogo",
    "% Conversão de pênalti",
    "% Pressão ganha/90",
    "% Bolas disputadas e ganhas (sem falta)",
    "%Faltas Sem Cartão",
    "% Passes certos",
    "% Passes em progressão em relação aos curtos",
    "% Des Ganhos",
    "% Des em relação a media",
    "% Cabeceios Ganhos",
    "% Cabs ganhos",
    "Eficácia defensiva",
}

# Colunas cujo valor já vem multiplicado por 100 (ex: 83.3), então só
# precisam do símbolo "%" acrescentado, sem multiplicar de novo.
PERCENTUAIS_JA_MULTIPLICADO = {
    "Jogos como Titular",
}



# Cada preset define um gráfico de dispersão pronto: quais métricas vão nos
# eixos X/Y e o texto interpretativo de cada quadrante (usado no script.js
# para desenhar os rótulos nos cantos do gráfico).
PRESETS_DISPERSAO = {
    "Construção": {
        "x": "Passes certos",
        "y": "Passes que são em progressão",
        "descricao": "Superior direito: construtores de elite. Superior esquerdo: criativos com baixo volume.",
        "quadrantes": {
            "sup_dir": "Construtores de elite",
            "sup_esq": "Criativos, baixo volume",
            "inf_dir": "Circula bola, poucas linhas quebradas",
            "inf_esq": "Baixa participação",
        },
    },
    "Segurança na Posse": {
        "x": "Passes certos",
        "y": "Posse perdida /90",
        "descricao": "Procure jogadores à direita e na parte inferior: muito passe, pouca perda.",
        "quadrantes": {
            "sup_dir": "Volume alto, mas arriscado",
            "sup_esq": "Baixo volume e inseguro",
            "inf_dir": "Seguro e produtivo",
            "inf_esq": "Discreto e seguro",
        },
    },
    "Equilíbrio Defensivo": {
        "x": "Movimentos de pressão ganhos",
        "y": "Desarmes ganhos",
        "descricao": "Separa volantes que só constroem dos que também recuperam a bola.",
        "quadrantes": {
            "sup_dir": "Defensor completo",
            "sup_esq": "Desarmador puro",
            "inf_dir": "Pressiona, mas não finaliza a jogada",
            "inf_esq": "Baixo envolvimento defensivo",
        },
    },
    "Criação": {
        "x": "Passes decisivos",
        "y": "Assistências Esperadas xA",
        "descricao": "Diferencia organizadores (passe) de criadores (chance real de gol).",
        "quadrantes": {
            "sup_dir": "Criadores de elite",
            "sup_esq": "Eficiente com poucas chances",
            "inf_dir": "Organizador, pouca chance clara",
            "inf_esq": "Baixa criação",
        },
    },
}


def formatar_valor(valor, coluna):
    """Filtro Jinja (`{{ valor | formatar(coluna) }}`) que decide como cada
    célula da tabela deve ser exibida, dependendo do tipo de métrica.

    Também é reaproveitado "na mão" (fora do Jinja) ao montar os dados do
    comparador e das rotas AJAX de perfil customizado / jogadores
    parecidos, já que ali as respostas são JSON, não HTML renderizado.
    """
    # Texto, datas etc. são exibidos como estão, sem formatação numérica.
    if not isinstance(valor, (int, float)):
        return valor

    if coluna in PERCENTUAIS_PROPORCAO:
        return f"{valor * 100:.1f}%"

    if coluna in PERCENTUAIS_JA_MULTIPLICADO:
        return f"{valor:.1f}%"

    # Demais números decimais: arredonda para 2 casas para não poluir a
    # tabela.
    if isinstance(valor, float):
        return round(valor, 2)

    return valor


app.jinja_env.filters["formatar"] = formatar_valor


def _extrair_ano_contrato(data_final):
    """Converte "Data Final de Contrato" (ex: "30/06/2027") no ano (2027),
    usado para o filtro "Contrato vence até" e para os badges de alerta.

    Jogadores sem data definida ("Sem Data Final") recebem o ano 9999, que
    funciona como um "infinito": nunca aciona o alerta de contrato próximo
    do fim e fica no final da lista de anos ordenada.
    """
    if isinstance(data_final, str) and data_final.split("/")[-1].isdigit():
        return int(data_final.split("/")[-1])
    return 9999


@app.route("/")
def inicio():
    """Página inicial: apresenta o projeto e explica cada funcionalidade
    antes de pedir o upload (que mora em GET /enviar).
    """
    return render_template("home.html")


@app.route("/login")
def login():
    """Inicia o login com Google: redireciona pro consentimento do Google,
    que depois volta pra /auth/callback abaixo.

    Se veio de um redirect automático do @login_required (ver
    login_manager.login_view acima), o Flask-Login já anexou
    "?next=/rota-original" na URL — guardamos isso na sessão pra voltar
    pra lá depois do login (ver auth_callback), já que o "next" da URL
    não sobrevive à ida-e-volta pro Google.
    """
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    proximo = request.args.get("next")
    if proximo and proximo.startswith("/") and not proximo.startswith("//"):
        # Só aceita caminhos relativos começando com uma única barra —
        # evita "open redirect" (ex: next=//site-malicioso.com ou
        # next=https://site-malicioso.com passando batido).
        session["_scouting_proximo_apos_login"] = proximo

    redirect_uri = url_for("auth_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    """Callback do Google após o consentimento: troca o código de
    autorização por um token, identifica (ou cria) a conta, adota os
    dados anônimos desta sessão (se houver — ver
    scouting/sessao.py::adotar_sessao_anonima) e loga o usuário."""
    token = oauth.google.authorize_access_token()
    info = token.get("userinfo") or {}

    google_sub = info.get("sub")
    if not google_sub:
        # Não deveria acontecer com o escopo "openid email profile", mas
        # evita um 500 feio se o Google devolver algo inesperado.
        return redirect(url_for("inicio"))

    usuario, _criado_agora = Usuario.obter_ou_criar(
        google_sub=google_sub,
        email=info.get("email", ""),
        nome=info.get("name", ""),
    )

    # Precisa vir ANTES de gravar CHAVE_USUARIO_ID na sessão: depois
    # disso, _id_sessao() (scouting/sessao.py) já devolve o ID da conta,
    # não dá mais pra achar a pasta anônima antiga a partir do "sessao".
    adotar_sessao_anonima(session, usuario.id)
    session[CHAVE_USUARIO_ID] = usuario.id

    login_user(usuario)

    proximo = session.pop("_scouting_proximo_apos_login", None)
    return redirect(proximo or url_for("inicio"))


@app.route("/logout")
def logout():
    logout_user()
    # Volta a ser uma sessão anônima "nova" a partir de agora (um UUID
    # novo é gerado no próximo upload) — não apaga nenhum dado da conta,
    # só para de usar a pasta dela nesta aba/navegador.
    session.pop(CHAVE_USUARIO_ID, None)
    return redirect(url_for("inicio"))


@app.route("/sw.js")
def service_worker():
    """Serve static/sw.js na raiz do site (/sw.js), não em /static/sw.js.

    O escopo máximo de um service worker é, por padrão, a pasta onde o
    arquivo é servido — em /static/sw.js ele só poderia controlar
    /static/*. Servindo em /sw.js, o escopo "/" declarado no register()
    (ver static/pwa-register.js) e no manifest.json cobre o site inteiro.
    """
    resposta = send_from_directory(app.static_folder, "sw.js")
    resposta.headers["Content-Type"] = "application/javascript"
    return resposta


@app.route("/enviar")
def enviar():
    """Tela do formulário de upload (separada da página inicial para dar
    espaço à apresentação do projeto em "/").
    """
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
@limiter.limit("10 per hour")
def upload():
    """Recebe o arquivo exportado do FM, processa e renderiza o dashboard.

    Fluxo: validar arquivo -> salvar com nome seguro -> carregar em
    DataFrame -> calcular métricas -> montar dados para cada aba/ranking/
    gráfico/comparador -> limpar o arquivo do disco -> renderizar o
    template.
    """
    arquivo = request.files.get("arquivo")

    if arquivo is None or arquivo.filename == "":
        return render_template(
            "upload.html", erro="Nenhum arquivo foi selecionado."
        ), 400

    if not extensao_permitida(arquivo.filename):
        return render_template(
            "upload.html",
            erro="Formato de arquivo não suportado. Envie um .csv, .xlsx ou .xls.",
        ), 400

    # Nome de arquivo sanitizado + prefixo único, para evitar path
    # traversal (ex: "../../etc/passwd") e colisões entre uploads
    # simultâneos.
    nome_seguro = secure_filename(arquivo.filename)
    nome_unico = f"{uuid.uuid4().hex}_{nome_seguro}"
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_unico)

    try:
        arquivo.save(caminho)

        # Cronometra só o bloco de parsing + cálculo de métricas (não o
        # resto da rota, que é montagem de dados para o template) — é
        # esse trecho que de fato pode demorar em arquivos grandes, e é
        # o número mostrado no feedback de upload (ver resultado.html).
        inicio_processamento = time.perf_counter()

        # Lê o arquivo bruto e aplica as fórmulas de cálculo (por 90 min,
        # percentuais, etc.) específicas do perfil "Volante".
        df = carregar_arquivo(caminho)

        # Nº de linhas lidas do arquivo, antes de qualquer cálculo — hoje
        # nenhuma linha é descartada por calcular_volantes, mas mantemos
        # esta contagem em separado de "jogadores válidos" (ver abaixo)
        # porque um parser mais rigoroso no futuro pode passar a
        # descartar linhas malformadas, e o usuário merece ver os dois
        # números quando isso acontecer.
        num_linhas_lidas = len(df)

        df = calcular_volantes(df)
        num_jogadores_validos = len(df)

        tempo_processamento = time.perf_counter() - inicio_processamento

        # Guarda o DataFrame calculado nesta sessão de navegador (não numa
        # variável global de processo) — assim as rotas AJAX (perfil
        # customizado, jogadores parecidos, melhor perfil) reaproveitam o
        # upload mais recente DESTA pessoa, sem interferir no que outras
        # pessoas estejam analisando ao mesmo tempo. Também é o export
        # usado como "jogador escoutado" na comparação com o elenco
        # (ver GET /elenco).
        salvar_export(session, df, nome_seguro)

        # --- Opções para os filtros da barra superior ---
        # Listas únicas de pé preferido e nacionalidade, usadas para
        # popular os <select> de filtro no template (resultado.html).
        opcoes_pe = sorted(df["Pé preferido"].dropna().unique().tolist())
        opcoes_nac = sorted(df["NAC"].dropna().unique().tolist())

        # Extrai o ano do contrato de cada jogador (ver
        # _extrair_ano_contrato) para alimentar o filtro "Contrato vence
        # até" e os badges de alerta de contrato perto do fim (vermelho =
        # ano mínimo, laranja = +1 ano).
        df["Ano Contrato"] = df["Data Final de Contrato"].apply(_extrair_ano_contrato)
        opcoes_ano_contrato = sorted(df["Ano Contrato"].unique().tolist())

        # 9999 representa "sem data definida" (ver _extrair_ano_contrato)
        # e não deve contar como o contrato mais próximo de vencer.
        anos_validos = [ano for ano in opcoes_ano_contrato if ano != 9999]
        ano_contrato_minimo = min(anos_validos) if anos_validos else None

        # As colunas de "Identidade" (nome, idade, clube...) aparecem
        # fixas em todas as tabelas; as demais chaves de COLUNAS_VOLANTES
        # viram uma aba cada uma na barra lateral.
        colunas_identidade = COLUNAS_VOLANTES["Identidade"]
        categorias_abas = {
            categoria: colunas
            for categoria, colunas in COLUNAS_VOLANTES.items()
            if categoria != "Identidade"
        }

        # Um dicionário de registros (linhas da tabela) por categoria/aba.
        # "Ano Contrato" vai junto para alimentar os data-attributes
        # usados pelos filtros em JavaScript (ver static/script.js ->
        # aplicarFiltros).
        dados_por_categoria = {
            categoria: df[colunas_identidade + colunas + ["Ano Contrato"]].to_dict(orient="records")
            for categoria, colunas in categorias_abas.items()
        }

        # --- Dados para o Comparador de Jogadores ---
        # Lista de nomes para popular os <select> do comparador e do
        # buscador de jogadores parecidos.
        lista_jogadores = df["Jogador"].tolist()

        # Para cada jogador, um dicionário {métrica: valor já formatado},
        # pronto para ser exibido lado a lado pelo JavaScript do
        # comparador (montarComparador em static/script.js), sem precisar
        # reprocessar formatação no front-end.
        dados_comparador = {}
        for registro in df.to_dict(orient="records"):
            nome = registro["Jogador"]
            linha = {}
            for categoria, colunas in categorias_abas.items():
                for coluna in colunas:
                    linha[coluna] = formatar_valor(registro[coluna], coluna)
            dados_comparador[nome] = linha

        # --- Identidade por jogador (para o painel "Favoritos & Notas") ---
        # Dicionário {jogador: {coluna_identidade: valor formatado}}, usado
        # no front-end para mostrar clube/idade/etc de cada jogador
        # favoritado sem precisar reprocessar nada no JavaScript.
        dados_identidade = {}
        for registro in df.to_dict(orient="records"):
            nome = registro["Jogador"]
            dados_identidade[nome] = {
                coluna: formatar_valor(registro[coluna], coluna)
                for coluna in colunas_identidade
            }

        # Intensidade (0 a 1) de cada célula, usada no template para
        # pintar o fundo mais forte quanto melhor for o valor do jogador
        # na métrica.
        intensidades_por_categoria = {
            categoria: calcular_intensidades(dados_por_categoria[categoria], colunas)
            for categoria, colunas in categorias_abas.items()
        }

        # Para cada perfil (Marcação, Construtor, Box-to-Box...), gera um
        # ranking próprio: normaliza as métricas do perfil e calcula a
        # "Nota do Perfil" ponderada pelos pesos definidos em
        # PERFIS_VOLANTES.
        rankings_por_perfil = {}
        for perfil, pesos in PERFIS_VOLANTES.items():
            df_ranking = calcular_ranking(df, pesos, nome_perfil=perfil)
            colunas_perfil = colunas_identidade + list(pesos.keys()) + ["Nota do Perfil", "Ano Contrato"]
            rankings_por_perfil[perfil] = df_ranking[colunas_perfil].to_dict(orient="records")

        # Mesma lógica de intensidade de cor, mas para as tabelas de
        # ranking por perfil (inclui a coluna extra "Nota do Perfil").
        intensidades_por_perfil = {
            perfil: calcular_intensidades(rankings_por_perfil[perfil], list(pesos.keys()) + ["Nota do Perfil"])
            for perfil, pesos in PERFIS_VOLANTES.items()
        }

        # Para o gráfico de dispersão: todas as colunas numéricas ficam
        # disponíveis no front-end, que escolhe X/Y de acordo com o
        # preset clicado (ver PRESETS_DISPERSAO e static/script.js).
        colunas_numericas = df.select_dtypes(include="number").columns.tolist()
        dados_dispersao = df[["Jogador"] + colunas_numericas].to_dict(orient="records")

    except (ArquivoInvalidoError, ColunaAusenteError, RankingColunaAusenteError) as erro:
        # Erros esperados de dados malformados/incompletos: mostramos a
        # mensagem amigável para o usuário em vez de um erro 500 cru.
        return render_template("upload.html", erro=str(erro)), 400

    except Exception:
        # Qualquer outra falha inesperada: log no servidor, mensagem
        # genérica para o usuário (não expomos detalhes internos/stack
        # trace).
        app.logger.exception("Erro inesperado ao processar upload")
        return render_template(
            "upload.html",
            erro="Ocorreu um erro inesperado ao processar o arquivo. "
                 "Verifique o formato e tente novamente.",
        ), 500

    finally:
        # Não guardamos os arquivos enviados além do necessário para
        # processá-los — evita que a pasta uploads/ cresça indefinidamente.
        if os.path.exists(caminho):
            os.remove(caminho)

    return render_template(
        "resultado.html",
        colunas_identidade=colunas_identidade,
        categorias=categorias_abas,
        dados=dados_por_categoria,
        intensidades=intensidades_por_categoria,
        perfis=PERFIS_VOLANTES,
        rankings=rankings_por_perfil,
        intensidades_perfil=intensidades_por_perfil,
        colunas_numericas=colunas_numericas,
        dados_dispersao=dados_dispersao,
        presets_dispersao=PRESETS_DISPERSAO,
        opcoes_pe=opcoes_pe,
        opcoes_nac=opcoes_nac,
        opcoes_ano_contrato=opcoes_ano_contrato,
        ano_contrato_minimo=ano_contrato_minimo,
        lista_jogadores=lista_jogadores,
        dados_comparador=dados_comparador,
        estrutura_categorias=categorias_abas,
        dados_identidade=dados_identidade,
        feedback_upload={
            "nome_arquivo": nome_seguro,
            "formato": os.path.splitext(nome_seguro)[1].lstrip(".").upper(),
            "num_linhas_lidas": num_linhas_lidas,
            "num_jogadores_validos": num_jogadores_validos,
            "tempo_processamento": tempo_processamento,
        },
    )


@app.route("/perfil-customizado", methods=["POST"])
def perfil_customizado():
    """Recalcula um ranking com pesos escolhidos livremente pelo usuário.

    Chamada via AJAX (fetch) por static/script.js (calcularPerfilCustomizado)
    depois que o usuário marca métricas e define pesos na aba "Perfil
    Customizado". Reaproveita calcular_ranking() — a mesma função usada
    para os perfis fixos de PERFIS_VOLANTES — só que com os pesos que
    vieram no corpo da requisição em vez de um dicionário fixo.
    """
    df_sessao = carregar_df_atual(session)

    if df_sessao is None:
        return jsonify({"erro": "Nenhum arquivo foi carregado ainda."}), 400

    dados_requisicao = request.get_json()
    pesos_brutos = dados_requisicao.get("pesos", {})

    # Ignora métricas com peso ausente/vazio/zero: não fazem sentido na
    # normalização (peso zero não influenciaria a nota de qualquer forma).
    pesos = {
        coluna: float(peso)
        for coluna, peso in pesos_brutos.items()
        if peso not in (None, "", 0)
    }

    if not pesos:
        return jsonify({"erro": "Selecione ao menos uma métrica com peso diferente de zero."}), 400

    try:
        colunas_identidade = COLUNAS_VOLANTES["Identidade"]
        df_ranking = calcular_ranking(df_sessao, pesos, nome_perfil="Perfil Customizado")
    except RankingColunaAusenteError as erro:
        return jsonify({"erro": str(erro)}), 400

    colunas_resultado = colunas_identidade + list(pesos.keys()) + ["Nota do Perfil"]
    registros = df_ranking[colunas_resultado].to_dict(orient="records")

    intensidades = calcular_intensidades(registros, list(pesos.keys()) + ["Nota do Perfil"])

    # Formata os valores da mesma forma que o Jinja faria no HTML (o
    # front-end aqui monta a tabela em JavaScript, então precisamos
    # devolver o texto já pronto para exibição).
    registros_formatados = []
    for registro in registros:
        linha = {}
        for chave, valor in registro.items():
            linha[chave] = round(valor, 1) if chave == "Nota do Perfil" else formatar_valor(valor, chave)
        registros_formatados.append(linha)

    return jsonify({
        "colunas_identidade": colunas_identidade,
        "colunas_metricas": list(pesos.keys()),
        "registros": registros_formatados,
        "intensidades": intensidades,
    })


@app.route("/jogadores-parecidos", methods=["POST"])
def jogadores_parecidos():
    """Busca os jogadores estatisticamente mais parecidos com um jogador
    de referência escolhido pelo usuário.

    Chamada via AJAX por static/script.js (buscarJogadoresParecidos).
    Delega o cálculo de similaridade para calcular_similares()
    (scouting/ranking.py) e devolve só as colunas de identidade + a
    porcentagem de similaridade de cada jogador encontrado.
    """
    df_sessao = carregar_df_atual(session)

    if df_sessao is None:
        return jsonify({"erro": "Nenhum arquivo foi carregado ainda."}), 400

    dados_requisicao = request.get_json()
    nome_jogador = dados_requisicao.get("jogador")

    if not nome_jogador:
        return jsonify({"erro": "Selecione um jogador."}), 400

    colunas_identidade = COLUNAS_VOLANTES["Identidade"]
    colunas_numericas = df_sessao.select_dtypes(include="number").columns.tolist()

    nomes, similaridades = calcular_similares(df_sessao, nome_jogador, colunas_numericas)

    if not nomes:
        return jsonify({"erro": "Jogador não encontrado."}), 400

    registros = []
    for nome, similaridade in zip(nomes, similaridades):
        linha_df = df_sessao[df_sessao["Jogador"] == nome][colunas_identidade]
        linha = linha_df.to_dict(orient="records")[0]
        linha_formatada = {chave: formatar_valor(valor, chave) for chave, valor in linha.items()}
        linha_formatada["Similaridade"] = similaridade
        registros.append(linha_formatada)

    return jsonify({
        "colunas_identidade": colunas_identidade,
        "registros": registros,
    })


@app.route("/melhor-perfil", methods=["POST"])
def melhor_perfil():
    """"Qual perfil combina comigo?" — o inverso do ranking normal.

    Em vez de partir de um perfil e listar os jogadores que mais se
    encaixam nele, esta rota parte de UM jogador e calcula sua "Nota do
    Perfil" em TODOS os perfis fixos (PERFIS_VOLANTES), devolvendo a lista
    ordenada do perfil que mais combina para o que menos combina.

    Chamada via AJAX pela mesma tela de "Jogadores Parecidos" (mesmo
    seletor de jogador), por static/script.js (buscarMelhorPerfil).
    """
    df_sessao = carregar_df_atual(session)

    if df_sessao is None:
        return jsonify({"erro": "Nenhum arquivo foi carregado ainda."}), 400

    dados_requisicao = request.get_json()
    nome_jogador = dados_requisicao.get("jogador")

    if not nome_jogador:
        return jsonify({"erro": "Selecione um jogador."}), 400

    if nome_jogador not in df_sessao["Jogador"].values:
        return jsonify({"erro": "Jogador não encontrado."}), 400

    resultados = []
    for perfil, pesos in PERFIS_VOLANTES.items():
        try:
            df_ranking = calcular_ranking(df_sessao, pesos, nome_perfil=perfil)
        except RankingColunaAusenteError as erro:
            return jsonify({"erro": str(erro)}), 400

        linha_jogador = df_ranking[df_ranking["Jogador"] == nome_jogador]
        nota = round(float(linha_jogador["Nota do Perfil"].iloc[0]), 1)
        resultados.append({"perfil": perfil, "nota": nota})

    resultados.sort(key=lambda item: item["nota"], reverse=True)

    return jsonify({"jogador": nome_jogador, "resultados": resultados})


def _contexto_elenco(erro=None):
    """Monta o contexto comum usado por GET /elenco e por
    /elenco/upload (quando precisa re-renderizar a mesma tela com um
    erro), evitando duplicar essa montagem nas duas rotas.
    """
    meta_elenco = elenco_metadata(session)
    if meta_elenco:
        try:
            data_hora = datetime.fromisoformat(meta_elenco["data_hora"])
            meta_elenco["data_hora_formatada"] = data_hora.strftime("%d/%m/%Y %H:%M")
        except (KeyError, ValueError):
            meta_elenco["data_hora_formatada"] = meta_elenco.get("data_hora", "-")

    df_scout = carregar_df_atual(session)
    df_elenco = carregar_elenco(session)

    return {
        "erro": erro,
        "meta_elenco": meta_elenco,
        "tem_export_scout": df_scout is not None,
        "lista_jogadores_scout": df_scout["Jogador"].tolist() if df_scout is not None else [],
        "lista_jogadores_elenco": df_elenco["Jogador"].tolist() if df_elenco is not None else [],
    }


@app.route("/elenco")
def elenco():
    """Tela do "meu time": upload do elenco do usuário e, se já houver um
    export escoutado nesta sessão, o formulário de comparação (ver POST
    /elenco/comparar, chamado via AJAX por static/elenco.js).
    """
    return render_template("elenco.html", **_contexto_elenco())


@app.route("/elenco/upload", methods=["POST"])
def elenco_upload():
    """Recebe o arquivo do elenco do usuário, processa com o mesmo
    parser/fórmulas do upload principal e salva como o elenco atual da
    sessão (substituindo um elenco anterior, se houver — ver
    salvar_elenco em scouting/sessao.py).
    """
    arquivo = request.files.get("arquivo")

    if arquivo is None or arquivo.filename == "":
        return render_template("elenco.html", **_contexto_elenco(
            erro="Nenhum arquivo foi selecionado."
        )), 400

    if not extensao_permitida(arquivo.filename):
        return render_template("elenco.html", **_contexto_elenco(
            erro="Formato de arquivo não suportado. Envie um .csv, .xlsx ou .xls."
        )), 400

    nome_seguro = secure_filename(arquivo.filename)
    nome_unico = f"{uuid.uuid4().hex}_{nome_seguro}"
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_unico)

    try:
        arquivo.save(caminho)
        df = carregar_arquivo(caminho)
        df = calcular_volantes(df)
        salvar_elenco(session, df, nome_seguro)
    except (ArquivoInvalidoError, ColunaAusenteError) as erro:
        return render_template("elenco.html", **_contexto_elenco(erro=str(erro))), 400
    except Exception:
        app.logger.exception("Erro inesperado ao processar upload de elenco")
        return render_template("elenco.html", **_contexto_elenco(
            erro="Ocorreu um erro inesperado ao processar o arquivo. "
                 "Verifique o formato e tente novamente."
        )), 500
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)

    return redirect(url_for("elenco"))


@app.route("/elenco/remover", methods=["POST"])
def elenco_remover():
    """Remove o elenco salvo desta sessão (botão "Trocar elenco" em
    templates/elenco.html)."""
    remover_elenco(session)
    return redirect(url_for("elenco"))


@app.route("/elenco/comparar", methods=["POST"])
def elenco_comparar():
    """Compara um jogador escoutado (do export mais recente desta sessão)
    com o elenco do usuário: contra um jogador específico do elenco, ou
    contra a média do elenco inteiro.

    Chamada via AJAX por static/elenco.js. Corpo esperado:
    {"jogador_scout": "Nome", "modo": "media" | "jogador",
     "jogador_elenco": "Nome" (obrigatório só quando modo == "jogador")}
    """
    dados_requisicao = request.get_json(silent=True) or {}
    nome_jogador_scout = dados_requisicao.get("jogador_scout")
    modo = dados_requisicao.get("modo")
    nome_jogador_elenco = dados_requisicao.get("jogador_elenco")

    if not nome_jogador_scout:
        return jsonify({"erro": "Selecione um jogador escoutado."}), 400

    if modo not in ("media", "jogador"):
        return jsonify({"erro": "Selecione o tipo de comparação."}), 400

    if modo == "jogador" and not nome_jogador_elenco:
        return jsonify({"erro": "Selecione um jogador do elenco para comparar."}), 400

    df_scout = carregar_df_atual(session)
    df_elenco = carregar_elenco(session)

    if df_scout is None:
        return jsonify({"erro": "Nenhum export escoutado encontrado nesta sessão."}), 400
    if df_elenco is None or df_elenco.empty:
        return jsonify({"erro": "Envie o elenco do seu time antes de comparar."}), 400

    if nome_jogador_scout not in df_scout["Jogador"].values:
        return jsonify({"erro": "Jogador escoutado não encontrado."}), 400
    if modo == "jogador" and nome_jogador_elenco not in df_elenco["Jogador"].values:
        return jsonify({"erro": "Jogador do elenco não encontrado."}), 400

    # "Nota do Perfil" do candidato, recalculada com o elenco como grupo
    # de referência (em vez dos demais jogadores escoutados) — é essa
    # normalização que responde "esse jogador é melhor que o que eu já
    # tenho?" em vez de "esse jogador é melhor que os outros escoutados?".
    notas_por_perfil = calcular_notas_vs_elenco(
        df_scout, df_elenco, nome_jogador_scout, PERFIS_VOLANTES
    )

    # Comparação métrica a métrica (mesmas categorias/colunas do resto do
    # dashboard), contra um jogador específico do elenco ou contra a
    # média do elenco.
    colunas_comparadas = [
        coluna
        for categoria, colunas in COLUNAS_VOLANTES.items()
        if categoria != "Identidade"
        for coluna in colunas
        if coluna in df_scout.columns and coluna in df_elenco.columns
    ]

    metricas_brutas = comparar_metricas_vs_elenco(
        df_scout,
        df_elenco,
        nome_jogador_scout,
        colunas_comparadas,
        jogador_elenco=nome_jogador_elenco if modo == "jogador" else None,
    )

    metricas_por_categoria = {}
    for categoria, colunas in COLUNAS_VOLANTES.items():
        if categoria == "Identidade":
            continue
        linhas = []
        for coluna in colunas:
            info = metricas_brutas.get(coluna)
            if info is None:
                continue
            linhas.append({
                "coluna": coluna,
                "scout": formatar_valor(info["scout"], coluna),
                "comparacao": formatar_valor(info["comparacao"], coluna),
                "melhor": info["melhor"],
            })
        if linhas:
            metricas_por_categoria[categoria] = linhas

    return jsonify({
        "jogador_scout": nome_jogador_scout,
        "modo": modo,
        "jogador_elenco": nome_jogador_elenco if modo == "jogador" else None,
        "notas_por_perfil": notas_por_perfil,
        "metricas": metricas_por_categoria,
    })


@app.route("/times")
@login_required
def times():
    """Lista os times do usuário logado + formulário de criar um novo
    (Fase 6, item 25)."""
    return render_template("times.html", times=current_user.times)


@app.route("/times", methods=["POST"])
@login_required
def times_criar():
    """Cria um time novo para o usuário logado."""
    nome = request.form.get("nome", "").strip()
    if not nome:
        return render_template(
            "times.html", times=current_user.times, erro="Dê um nome para o time."
        ), 400

    if Time.query.filter_by(usuario_id=current_user.id, nome=nome).first() is not None:
        return render_template(
            "times.html", times=current_user.times,
            erro=f'Você já tem um time chamado "{nome}".',
        ), 400

    db.session.add(Time(usuario_id=current_user.id, nome=nome))
    db.session.commit()
    return redirect(url_for("times"))


def _obter_time_do_usuario_ou_404(time_id):
    """Busca um Time pelo ID, garantindo que pertence ao usuário logado —
    devolve 404 (não 403) tanto para um time inexistente quanto para um
    time de outra conta, pra não vazar quais IDs existem."""
    time = db.session.get(Time, time_id)
    if time is None or time.usuario_id != current_user.id:
        abort(404)
    return time


@app.route("/times/<int:time_id>")
@login_required
def time_detalhe(time_id):
    """Detalhe de um Time: lista as Temporadas já enviadas + formulário
    de upload de uma nova (Fase 6, item 26)."""
    time = _obter_time_do_usuario_ou_404(time_id)
    return render_template("time_detalhe.html", time=time)


@app.route("/times/<int:time_id>/renomear", methods=["POST"])
@login_required
def time_renomear(time_id):
    time = _obter_time_do_usuario_ou_404(time_id)
    novo_nome = request.form.get("nome", "").strip()
    if not novo_nome:
        return render_template("time_detalhe.html", time=time, erro="Dê um nome para o time."), 400

    time.nome = novo_nome
    db.session.commit()
    return redirect(url_for("time_detalhe", time_id=time.id))


@app.route("/times/<int:time_id>/excluir", methods=["POST"])
@login_required
def time_excluir(time_id):
    """Exclui o time e todas as Temporadas vinculadas a ele (cascade —
    ver relacionamento em scouting/models.py). Não apaga os arquivos
    .pkl em session_cache/ (ficam órfãos até a limpeza por idade de
    scripts/limpar_sessoes_antigas.py) — remover isso também fica para
    quando o Bloco B tiver testes de integração cobrindo esse caminho.
    """
    time = _obter_time_do_usuario_ou_404(time_id)
    db.session.delete(time)
    db.session.commit()
    return redirect(url_for("times"))


@app.route("/times/<int:time_id>/temporadas", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def time_temporada_upload(time_id):
    """Recebe um export do FM vinculado a este Time + rótulo de
    temporada (ex: "2025/26") — Fase 6, item 26.

    Reaproveita o mesmo parser/fórmulas do upload principal (POST
    /upload), mas guarda o resultado como uma Temporada em vez de "o
    último export desta sessão": itens 27+ (comparação entre
    temporadas) vão ler daqui.
    """
    time = _obter_time_do_usuario_ou_404(time_id)

    rotulo = request.form.get("rotulo", "").strip()
    arquivo = request.files.get("arquivo")

    if not rotulo:
        return render_template("time_detalhe.html", time=time, erro="Informe o rótulo da temporada (ex: 2025/26).") , 400

    if arquivo is None or arquivo.filename == "":
        return render_template("time_detalhe.html", time=time, erro="Nenhum arquivo foi selecionado."), 400

    if not extensao_permitida(arquivo.filename):
        return render_template(
            "time_detalhe.html", time=time,
            erro="Formato de arquivo não suportado. Envie um .csv, .xlsx ou .xls.",
        ), 400

    nome_seguro = secure_filename(arquivo.filename)
    nome_unico = f"{uuid.uuid4().hex}_{nome_seguro}"
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_unico)

    try:
        arquivo.save(caminho)
        df = carregar_arquivo(caminho)
        df = calcular_volantes(df)
        export_id = salvar_export(session, df, nome_seguro)
        Temporada.registrar(
            time=time,
            rotulo=rotulo,
            export_id=export_id,
            nome_arquivo=nome_seguro,
            num_jogadores=len(df),
        )
    except (ArquivoInvalidoError, ColunaAusenteError) as erro:
        return render_template("time_detalhe.html", time=time, erro=str(erro)), 400
    except Exception:
        app.logger.exception("Erro inesperado ao processar upload de temporada")
        return render_template(
            "time_detalhe.html", time=time,
            erro="Ocorreu um erro inesperado ao processar o arquivo. "
                 "Verifique o formato e tente novamente.",
        ), 500
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)

    return redirect(url_for("time_detalhe", time_id=time.id))


@app.errorhandler(413)
def arquivo_muito_grande(_erro):
    """Página amigável quando o upload excede MAX_CONTENT_LENGTH (15 MB)."""
    return render_template(
        "upload.html",
        erro="O arquivo enviado é muito grande (limite de 15 MB).",
    ), 413


@app.errorhandler(429)
def limite_de_requisicoes_excedido(_erro):
    """Página amigável quando o limite de uploads por hora (ver
    @limiter.limit em POST /upload) é excedido, em vez do erro genérico
    do Flask-Limiter.
    """
    return render_template(
        "upload.html",
        erro="Muitos uploads em pouco tempo. Aguarde um pouco e tente novamente.",
    ), 429


if __name__ == "__main__":
    # Cria as tabelas do banco (scouting/models.py) se ainda não
    # existirem — conveniente para "python app.py" em desenvolvimento
    # local. Em produção (gunicorn), rode
    # `python scripts/inicializar_banco.py` manualmente uma vez antes do
    # primeiro deploy (ver DEPLOY.md) — este bloco não roda nesse caso.
    with app.app_context():
        db.create_all()

    # DEBUG nunca deve ficar ligado em produção: expõe um console Python
    # interativo que permite execução remota de código. Controlado por
    # variável de ambiente, desligado por padrão.
    modo_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=modo_debug)
