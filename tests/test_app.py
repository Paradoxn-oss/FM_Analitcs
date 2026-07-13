"""
Testes de integração leves: sobem o app Flask de verdade (via test_client)
e batem nas rotas, sem mockar nada — servem pra pegar problemas que só
aparecem na "cola" entre as camadas (ex: um valor numpy que passa limpo
nos testes unitários de scouting/ranking.py mas quebra a serialização JSON
lá em app.py — foi exatamente assim que um bug real foi pego durante o
desenvolvimento do histórico de exports).

Isolamento: scouting/sessao.py e app.py usam pastas RELATIVAS
("session_cache/", "uploads/") por padrão. Em vez de tentar sobrescrever
esse valor padrão via monkeypatch (não funcionaria: argumentos padrão em
Python são resolvidos uma única vez, na definição da função, não a cada
chamada), a fixture `isola_diretorio_trabalho` muda o diretório de
trabalho do processo para uma pasta temporária — assim os arquivos
criados durante os testes não se acumulam dentro do repositório real.
"""

import io

import pytest

import app as app_module


@pytest.fixture
def isola_diretorio_trabalho(tmp_path, monkeypatch, banco_limpo):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "uploads").mkdir(exist_ok=True)


@pytest.fixture
def client(isola_diretorio_trabalho):
    app_module.app.config["TESTING"] = True
    # Desliga o rate limiting do POST /upload (ver app.py) por padrão nos
    # testes: sem isso, o estado do limiter (em memória, por IP) fica
    # compartilhado entre TODOS os testes que usam esta fixture na mesma
    # sessão do pytest — vários testes têm 127.0.0.1 como "IP" do test
    # client e poderiam acabar tomando 429 dependendo da ordem/quantidade
    # de testes rodados, sem relação nenhuma com o que cada teste
    # individual está verificando. O comportamento do rate limit em si é
    # testado à parte, com o limiter reativado (ver TestRateLimitUpload).
    #
    # IMPORTANTE: o Flask-Limiter 3.x lê RATELIMIT_ENABLED de app.config
    # só UMA VEZ, dentro de init_app() (via config.setdefault), e guarda o
    # resultado no atributo limiter.enabled. Mudar app.config depois que o
    # app já subiu não tem efeito nenhum na checagem feita a cada request
    # — quem precisa ser alterado de verdade é limiter.enabled diretamente.
    app_module.limiter.enabled = False
    with app_module.app.test_client() as client:
        yield client


@pytest.fixture
def csv_valido_bytes(df_fm_bruto):
    """Bytes de um CSV válido (mesmas colunas do export do FM), pronto pra
    ser enviado como upload multipart no test client.
    """
    buffer = io.StringIO()
    df_fm_bruto.to_csv(buffer, index=False, sep=";")
    return buffer.getvalue().encode("utf-8")


class TestUpload:
    def test_upload_valido_devolve_200_com_dashboard(self, client, csv_valido_bytes):
        resposta = client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "export.csv")},
            content_type="multipart/form-data",
        )
        assert resposta.status_code == 200
        assert b"Jogador Ofensivo" in resposta.data

    def test_upload_sem_arquivo_devolve_400(self, client):
        resposta = client.post("/upload", data={}, content_type="multipart/form-data")
        assert resposta.status_code == 400

    def test_upload_extensao_invalida_devolve_400(self, client):
        resposta = client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(b"lixo"), "export.exe")},
            content_type="multipart/form-data",
        )
        assert resposta.status_code == 400


class TestRotasAjaxPrecisamDeUploadPrevio:
    """As rotas AJAX (perfil customizado, jogadores parecidos, melhor
    perfil) dependem de um upload feito antes NA MESMA SESSÃO — sem isso,
    devem devolver um 400 com mensagem amigável, nunca um 500.
    """

    def test_perfil_customizado_sem_upload(self, client):
        resposta = client.post("/perfil-customizado", json={"pesos": {"Gols": 1}})
        assert resposta.status_code == 400

    def test_jogadores_parecidos_sem_upload(self, client):
        resposta = client.post("/jogadores-parecidos", json={"jogador": "Fulano"})
        assert resposta.status_code == 400

    def test_melhor_perfil_sem_upload(self, client):
        resposta = client.post("/melhor-perfil", json={"jogador": "Fulano"})
        assert resposta.status_code == 400


class TestFluxoCompletoAposUpload:
    @pytest.fixture
    def client_com_upload(self, client, csv_valido_bytes):
        client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "export.csv")},
            content_type="multipart/form-data",
        )
        return client

    def test_melhor_perfil_devolve_todos_os_perfis_ordenados(self, client_com_upload):
        resposta = client_com_upload.post("/melhor-perfil", json={"jogador": "Jogador Ofensivo"})
        assert resposta.status_code == 200
        dados = resposta.get_json()
        notas = [item["nota"] for item in dados["resultados"]]
        assert notas == sorted(notas, reverse=True)

    def test_jogadores_parecidos_nao_inclui_o_proprio_jogador(self, client_com_upload):
        resposta = client_com_upload.post("/jogadores-parecidos", json={"jogador": "Jogador Ofensivo"})
        assert resposta.status_code == 200
        nomes = [registro["Jogador"] for registro in resposta.get_json()["registros"]]
        assert "Jogador Ofensivo" not in nomes

    def test_perfil_customizado_com_pesos_validos(self, client_com_upload):
        resposta = client_com_upload.post("/perfil-customizado", json={"pesos": {"Gols": 2}})
        assert resposta.status_code == 200

    def test_perfil_customizado_sem_pesos_validos_devolve_400(self, client_com_upload):
        resposta = client_com_upload.post("/perfil-customizado", json={"pesos": {"Gols": 0}})
        assert resposta.status_code == 400


class TestSessaoIsolaUploadsEntreClientes:
    def test_cliente_sem_upload_nao_ve_dados_de_outro_cliente(self, isola_diretorio_trabalho, csv_valido_bytes):
        app_module.app.config["TESTING"] = True
        cliente_a = app_module.app.test_client()
        cliente_b = app_module.app.test_client()

        cliente_a.post(
            "/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "export.csv")},
            content_type="multipart/form-data",
        )

        resposta_b = cliente_b.post("/melhor-perfil", json={"jogador": "Jogador Ofensivo"})
        assert resposta_b.status_code == 400

        resposta_a = cliente_a.post("/melhor-perfil", json={"jogador": "Jogador Ofensivo"})
        assert resposta_a.status_code == 200


class TestRateLimitUpload:
    """POST /upload tem um limite de 10 requisições/hora por IP (ver
    @limiter.limit em app.py) — protege o app de abuso de CPU no plano
    gratuito do PythonAnywhere. A fixture `client` padrão desliga esse
    limite (ver docstring dela) pra não afetar os outros testes; aqui ele
    é reativado de propósito.
    """

    @pytest.fixture
    def client_com_limite_ativo(self, isola_diretorio_trabalho):
        app_module.app.config["TESTING"] = True
        # Ver o comentário em client() acima: quem controla a checagem de
        # rate limit em tempo de requisição é limiter.enabled, não
        # app.config["RATELIMIT_ENABLED"] (que só é lido uma vez, em
        # init_app, no boot do app).
        app_module.limiter.enabled = True
        # O storage do limiter é em memória e compartilhado pelo processo
        # (não é recriado por request) — sem resetar, contagens de outros
        # testes/execuções anteriores vazariam pra este teste.
        app_module.limiter.reset()
        with app_module.app.test_client() as client:
            yield client
        # Restaura o estado padrão dos testes (rate limit desligado) para
        # não vazar para as próximas classes/testes que rodarem depois.
        app_module.limiter.enabled = False

    def test_upload_alem_do_limite_devolve_429(self, client_com_limite_ativo, csv_valido_bytes):
        cliente = client_com_limite_ativo

        for _ in range(10):
            resposta = cliente.post(
                "/upload",
                data={"arquivo": (io.BytesIO(csv_valido_bytes), "export.csv")},
                content_type="multipart/form-data",
            )
            assert resposta.status_code == 200

        resposta_extra = cliente.post(
            "/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "export.csv")},
            content_type="multipart/form-data",
        )
        assert resposta_extra.status_code == 429


class TestElenco:
    def test_pagina_elenco_sem_elenco_enviado(self, client):
        resposta = client.get("/elenco")
        assert resposta.status_code == 200
        assert "escolher o export do seu elenco".encode("utf-8") in resposta.data

    def test_upload_de_elenco_mostra_status_na_pagina(self, client, csv_valido_bytes):
        resposta_upload = client.post(
            "/elenco/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "meu_time.csv")},
            content_type="multipart/form-data",
        )
        assert resposta_upload.status_code == 302

        resposta = client.get("/elenco")
        assert resposta.status_code == 200
        assert b"meu_time.csv" in resposta.data

    def test_upload_de_elenco_sem_arquivo_devolve_400(self, client):
        resposta = client.post("/elenco/upload", data={}, content_type="multipart/form-data")
        assert resposta.status_code == 400

    def test_trocar_elenco_remove_o_elenco_atual(self, client, csv_valido_bytes):
        client.post(
            "/elenco/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "meu_time.csv")},
            content_type="multipart/form-data",
        )
        client.post("/elenco/remover")

        resposta = client.get("/elenco")
        assert b"meu_time.csv" not in resposta.data

    def test_comparar_sem_elenco_enviado_devolve_400(self, client, csv_valido_bytes):
        client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "escoutados.csv")},
            content_type="multipart/form-data",
        )
        resposta = client.post(
            "/elenco/comparar",
            json={"jogador_scout": "Jogador Ofensivo", "modo": "media"},
        )
        assert resposta.status_code == 400

    def test_comparar_com_media_do_elenco(self, client, df_fm_bruto):
        # Export escoutado: os 3 jogadores do fixture padrão.
        buffer_scout = io.StringIO()
        df_fm_bruto.to_csv(buffer_scout, index=False, sep=";")
        client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(buffer_scout.getvalue().encode("utf-8")), "escoutados.csv")},
            content_type="multipart/form-data",
        )

        # Elenco: mesmas colunas, jogadores com outros nomes (o próprio
        # time do usuário).
        df_elenco = df_fm_bruto.copy()
        df_elenco["Jogador"] = ["Titular 1", "Titular 2", "Titular 3"]
        buffer_elenco = io.StringIO()
        df_elenco.to_csv(buffer_elenco, index=False, sep=";")
        client.post(
            "/elenco/upload",
            data={"arquivo": (io.BytesIO(buffer_elenco.getvalue().encode("utf-8")), "meu_time.csv")},
            content_type="multipart/form-data",
        )

        resposta = client.post(
            "/elenco/comparar",
            json={"jogador_scout": "Jogador Ofensivo", "modo": "media"},
        )
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert dados["jogador_scout"] == "Jogador Ofensivo"
        assert dados["jogador_elenco"] is None
        assert len(dados["notas_por_perfil"]) > 0
        assert "Gols" in {linha["coluna"] for linhas in dados["metricas"].values() for linha in linhas}

    def test_comparar_com_jogador_especifico_do_elenco(self, client, df_fm_bruto):
        buffer_scout = io.StringIO()
        df_fm_bruto.to_csv(buffer_scout, index=False, sep=";")
        client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(buffer_scout.getvalue().encode("utf-8")), "escoutados.csv")},
            content_type="multipart/form-data",
        )

        df_elenco = df_fm_bruto.copy()
        df_elenco["Jogador"] = ["Titular 1", "Titular 2", "Titular 3"]
        buffer_elenco = io.StringIO()
        df_elenco.to_csv(buffer_elenco, index=False, sep=";")
        client.post(
            "/elenco/upload",
            data={"arquivo": (io.BytesIO(buffer_elenco.getvalue().encode("utf-8")), "meu_time.csv")},
            content_type="multipart/form-data",
        )

        resposta = client.post(
            "/elenco/comparar",
            json={"jogador_scout": "Jogador Ofensivo", "modo": "jogador", "jogador_elenco": "Titular 1"},
        )
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert dados["jogador_elenco"] == "Titular 1"

    def test_comparar_sem_jogador_scout_devolve_400(self, client):
        resposta = client.post("/elenco/comparar", json={"modo": "media"})
        assert resposta.status_code == 400

    def test_comparar_modo_jogador_sem_jogador_elenco_devolve_400(self, client, csv_valido_bytes):
        client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "escoutados.csv")},
            content_type="multipart/form-data",
        )
        client.post(
            "/elenco/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "meu_time.csv")},
            content_type="multipart/form-data",
        )
        resposta = client.post(
            "/elenco/comparar",
            json={"jogador_scout": "Jogador Ofensivo", "modo": "jogador"},
        )
        assert resposta.status_code == 400


@pytest.fixture
def google_devolve(monkeypatch):
    """Fábrica de fake do retorno do Google: chame
    `google_devolve(sub=..., email=..., nome=...)` antes de bater em
    /auth/callback. Fica em nível de módulo (não só dentro de TestLogin)
    porque TestMeusTimes também precisa logar um usuário de teste."""
    def _configurar(sub="sub-teste", email="fulano@example.com", nome="Fulano de Tal"):
        token_falso = {"userinfo": {"sub": sub, "email": email, "name": nome}}
        monkeypatch.setattr(
            app_module.oauth.google,
            "authorize_access_token",
            lambda *args, **kwargs: token_falso,
        )
    return _configurar


@pytest.fixture
def client_logado(client, google_devolve):
    """Um test client já logado (ver google_devolve acima) — conveniência
    para testes que precisam de um usuário autenticado mas não estão
    testando o fluxo de login em si (ex: TestMeusTimes)."""
    google_devolve(sub="sub-teste", email="fulano@example.com", nome="Fulano de Tal")
    client.get("/auth/callback")
    return client


class TestLogin:
    """Testes de integração do login com Google (Fase 6, itens 20 e 21).

    Não há como testar o fluxo real do OAuth do Google aqui (exigiria
    acesso de rede de verdade e uma conta Google de teste) — o que estes
    testes cobrem é a "cola" do lado de dentro do app: dado que o Google
    devolveu um token válido, o app cria/recupera a conta certa, adota os
    dados anônimos já enviados, e o estado de login fica visível nas
    páginas. O monkeypatch troca só a chamada que fala com o Google
    (authorize_access_token); todo o resto (scouting/models, scouting/sessao,
    Flask-Login) roda de verdade.
    """

    def test_home_mostra_botao_de_entrar_quando_anonimo(self, client):
        resposta = client.get("/")
        assert b"Entrar com Google" in resposta.data

    def test_callback_cria_conta_e_loga(self, client, google_devolve):
        google_devolve(sub="sub-123", email="fulano@example.com", nome="Fulano de Tal")

        resposta = client.get("/auth/callback", follow_redirects=True)

        assert resposta.status_code == 200
        assert "Fulano de Tal".encode("utf-8") in resposta.data
        assert b"Entrar com Google" not in resposta.data

    def test_segundo_login_recupera_a_mesma_conta(self, client, google_devolve):
        google_devolve(sub="sub-123", email="fulano@example.com", nome="Fulano de Tal")
        client.get("/auth/callback")
        client.get("/logout")

        google_devolve(sub="sub-123", email="fulano@example.com", nome="Fulano de Tal")
        client.get("/auth/callback")

        with app_module.app.app_context():
            contas = app_module.Usuario.query.all()
            assert len(contas) == 1  # não duplicou a conta no segundo login

    def test_logout_volta_a_mostrar_botao_de_entrar(self, client, google_devolve):
        google_devolve()
        client.get("/auth/callback")

        client.get("/logout")
        resposta = client.get("/")

        assert b"Entrar com Google" in resposta.data

    def test_login_adota_exports_enviados_antes_de_logar(self, client, google_devolve, csv_valido_bytes):
        # Envia um export ainda anônimo...
        client.post(
            "/upload",
            data={"arquivo": (io.BytesIO(csv_valido_bytes), "escoutados.csv")},
            content_type="multipart/form-data",
        )

        # ...depois loga...
        google_devolve(sub="sub-123", email="fulano@example.com", nome="Fulano de Tal")
        client.get("/auth/callback")

        # ...e o export de antes do login continua sendo "o atual" (não
        # precisa reenviar o arquivo).
        resposta = client.post("/perfil-customizado", json={"pesos": {"Passes certos": 1.0}})
        assert resposta.status_code == 200


class TestMeusTimes:
    """Testes de integração das rotas de Times/Temporadas (Fase 6, itens
    25 e 26 do ROADMAP_FASE6.md)."""

    def test_anonimo_e_redirecionado_para_login(self, client):
        resposta = client.get("/times")
        assert resposta.status_code == 302
        assert "/login" in resposta.headers["Location"]

    def test_criar_time(self, client_logado):
        resposta = client_logado.post("/times", data={"nome": "Botafogo"}, follow_redirects=True)

        assert resposta.status_code == 200
        assert b"Botafogo" in resposta.data

    def test_criar_time_sem_nome_devolve_400(self, client_logado):
        resposta = client_logado.post("/times", data={"nome": "  "})
        assert resposta.status_code == 400

    def test_nao_pode_repetir_nome_de_time(self, client_logado):
        client_logado.post("/times", data={"nome": "Botafogo"})
        resposta = client_logado.post("/times", data={"nome": "Botafogo"})

        assert resposta.status_code == 400
        assert "já tem um time".encode("utf-8") in resposta.data

    def test_time_de_outro_usuario_devolve_404(self, client_logado, google_devolve):
        client_logado.post("/times", data={"nome": "Botafogo"})
        with app_module.app.app_context():
            time_id = app_module.Time.query.filter_by(nome="Botafogo").first().id

        # Loga como uma SEGUNDA conta, diferente de quem criou o time.
        google_devolve(sub="outra-conta", email="outro@example.com", nome="Outra Pessoa")
        client_logado.get("/auth/callback")

        resposta = client_logado.get(f"/times/{time_id}")
        assert resposta.status_code == 404

    def test_renomear_time(self, client_logado):
        client_logado.post("/times", data={"nome": "Botafogo"})
        with app_module.app.app_context():
            time_id = app_module.Time.query.filter_by(nome="Botafogo").first().id

        resposta = client_logado.post(
            f"/times/{time_id}/renomear", data={"nome": "Botafogo FC"}, follow_redirects=True
        )

        assert resposta.status_code == 200
        assert b"Botafogo FC" in resposta.data

    def test_excluir_time(self, client_logado):
        client_logado.post("/times", data={"nome": "Botafogo"})
        with app_module.app.app_context():
            time_id = app_module.Time.query.filter_by(nome="Botafogo").first().id

        resposta = client_logado.post(f"/times/{time_id}/excluir", follow_redirects=True)

        assert resposta.status_code == 200
        # "Botafogo" sozinho não serve de asserção aqui: o placeholder do
        # formulário de criar time usa esse nome como exemplo, então
        # sempre aparece na página, mesmo com a lista vazia.
        assert b"Voc\xc3\xaa ainda n\xc3\xa3o criou nenhum time." in resposta.data
        with app_module.app.app_context():
            assert app_module.Time.query.count() == 0

    def test_upload_de_temporada_cria_registro_vinculado_ao_time(self, client_logado, csv_valido_bytes):
        client_logado.post("/times", data={"nome": "Botafogo"})
        with app_module.app.app_context():
            time_id = app_module.Time.query.filter_by(nome="Botafogo").first().id

        resposta = client_logado.post(
            f"/times/{time_id}/temporadas",
            data={
                "rotulo": "2025/26",
                "arquivo": (io.BytesIO(csv_valido_bytes), "escoutados.csv"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert resposta.status_code == 200
        assert "2025/26".encode("utf-8") in resposta.data

        with app_module.app.app_context():
            temporada = app_module.Temporada.query.filter_by(time_id=time_id, rotulo="2025/26").first()
            assert temporada is not None
            assert temporada.num_jogadores == 3
            assert temporada.nome_arquivo == "escoutados.csv"

    def test_reenviar_mesmo_rotulo_atualiza_em_vez_de_duplicar(self, client_logado, csv_valido_bytes):
        client_logado.post("/times", data={"nome": "Botafogo"})
        with app_module.app.app_context():
            time_id = app_module.Time.query.filter_by(nome="Botafogo").first().id

        for _ in range(2):
            client_logado.post(
                f"/times/{time_id}/temporadas",
                data={
                    "rotulo": "2025/26",
                    "arquivo": (io.BytesIO(csv_valido_bytes), "escoutados.csv"),
                },
                content_type="multipart/form-data",
            )

        with app_module.app.app_context():
            total = app_module.Temporada.query.filter_by(time_id=time_id, rotulo="2025/26").count()
            assert total == 1

    def test_upload_de_temporada_sem_rotulo_devolve_400(self, client_logado, csv_valido_bytes):
        client_logado.post("/times", data={"nome": "Botafogo"})
        with app_module.app.app_context():
            time_id = app_module.Time.query.filter_by(nome="Botafogo").first().id

        resposta = client_logado.post(
            f"/times/{time_id}/temporadas",
            data={"rotulo": "", "arquivo": (io.BytesIO(csv_valido_bytes), "escoutados.csv")},
            content_type="multipart/form-data",
        )
        assert resposta.status_code == 400
