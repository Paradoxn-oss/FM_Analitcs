"""
Testes de scouting/sessao.py: armazenamento de DataFrames por sessão de
usuário (item "Sessão por usuário" da Fase 2 do roadmap).

Todas as funções recebem `sessao` como um dict comum (em vez de
flask.session) — o próprio módulo foi desenhado para aceitar qualquer
objeto tipo dicionário, então testamos sem precisar de um contexto de
requisição Flask (ver docstring de scouting/sessao.py).
"""

import pandas as pd
import pytest

from scouting.sessao import (
    CHAVE_ID_SESSAO,
    CHAVE_USUARIO_ID,
    MAX_EXPORTS_POR_SESSAO,
    adotar_sessao_anonima,
    carregar_df_atual,
    carregar_export,
    export_id_valido,
    listar_exports,
    salvar_export,
)


@pytest.fixture
def df_exemplo():
    return pd.DataFrame({"Jogador": ["Fulano", "Ciclano"], "Gols": [5, 3]})


class TestSalvarECarregarExport:
    def test_round_trip_preserva_os_dados(self, tmp_path, df_exemplo):
        sessao = {}
        export_id = salvar_export(sessao, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        df_carregado = carregar_export(sessao, export_id, pasta_base=str(tmp_path))

        pd.testing.assert_frame_equal(df_carregado, df_exemplo)

    def test_export_marcado_como_ultimo_da_sessao(self, tmp_path, df_exemplo):
        sessao = {}
        export_id = salvar_export(sessao, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        df_atual = carregar_df_atual(sessao, pasta_base=str(tmp_path))

        pd.testing.assert_frame_equal(df_atual, df_exemplo)
        assert export_id  # é um uuid não-vazio

    def test_segundo_upload_substitui_o_ultimo_mas_mantem_o_primeiro(self, tmp_path, df_exemplo):
        sessao = {}
        id_1 = salvar_export(sessao, df_exemplo, "primeiro.csv", pasta_base=str(tmp_path))
        df_2 = pd.DataFrame({"Jogador": ["Beltrano"], "Gols": [1]})
        id_2 = salvar_export(sessao, df_2, "segundo.csv", pasta_base=str(tmp_path))

        # "ultimo" agora é o segundo export...
        df_atual = carregar_df_atual(sessao, pasta_base=str(tmp_path))
        pd.testing.assert_frame_equal(df_atual, df_2)

        # ...mas o primeiro continua acessível pelo histórico.
        df_primeiro = carregar_export(sessao, id_1, pasta_base=str(tmp_path))
        pd.testing.assert_frame_equal(df_primeiro, df_exemplo)
        assert id_1 != id_2


class TestCarregarExportInexistente:
    def test_id_invalido_devolve_none(self, tmp_path, df_exemplo):
        sessao = {}
        salvar_export(sessao, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        assert carregar_export(sessao, "id-que-nao-existe", pasta_base=str(tmp_path)) is None

    def test_sessao_sem_nenhum_upload_devolve_none(self, tmp_path):
        sessao = {}
        assert carregar_df_atual(sessao, pasta_base=str(tmp_path)) is None

    def test_sessao_completamente_nova_nao_cria_id_ao_so_ler(self, tmp_path):
        # Ler não deve "gastar"/criar um ID de sessão para quem nunca fez
        # upload — listar_exports numa sessão nova deve ser só uma lista
        # vazia, sem erro.
        sessao = {}
        assert listar_exports(sessao, pasta_base=str(tmp_path)) == []


class TestExportIdValido:
    """Formato esperado é hex de 32 caracteres (uuid4().hex) — ver
    scouting/sessao.py::export_id_valido. Fecha risco de path traversal
    em carregar_export() (usado por POST /historico/comparar em app.py,
    onde export_id vem cru do corpo de um POST).
    """

    def test_uuid_hex_valido_e_aceito(self):
        assert export_id_valido("a" * 32) is True
        assert export_id_valido("0123456789abcdef0123456789abcdef") is True

    def test_tentativa_de_path_traversal_e_rejeitada(self):
        assert export_id_valido("../../../../etc/passwd") is False
        assert export_id_valido("../outra_sessao/algum_id") is False

    def test_tamanho_ou_caracteres_errados_sao_rejeitados(self):
        assert export_id_valido("a" * 31) is False       # curto demais
        assert export_id_valido("a" * 33) is False        # longo demais
        assert export_id_valido("A" * 32) is False         # maiúsculas não são hex válido aqui
        assert export_id_valido("g" * 32) is False          # 'g' não é dígito hex
        assert export_id_valido("") is False
        assert export_id_valido(None) is False

    def test_carregar_export_com_id_malicioso_devolve_none_sem_tocar_disco(
        self, tmp_path, df_exemplo
    ):
        sessao = {}
        salvar_export(sessao, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        # Mesmo com uma sessão válida e um export existente, um export_id
        # fora do formato esperado nunca deve resultar em nada além de
        # None — em especial, nunca deve ler um arquivo fora da pasta da
        # sessão.
        assert carregar_export(sessao, "../../etc/passwd", pasta_base=str(tmp_path)) is None


class TestIsolamentoEntreSessoes:
    def test_sessoes_diferentes_nao_enxergam_os_exports_uma_da_outra(self, tmp_path, df_exemplo):
        sessao_a = {}
        sessao_b = {}

        export_id = salvar_export(sessao_a, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        # sessão B não tem esse export nem um "último" export próprio.
        assert carregar_export(sessao_b, export_id, pasta_base=str(tmp_path)) is None
        assert carregar_df_atual(sessao_b, pasta_base=str(tmp_path)) is None

        # sessão A continua funcionando normalmente.
        assert carregar_df_atual(sessao_a, pasta_base=str(tmp_path)) is not None

    def test_cada_sessao_ganha_um_id_diferente(self, tmp_path, df_exemplo):
        sessao_a, sessao_b = {}, {}
        salvar_export(sessao_a, df_exemplo, "a.csv", pasta_base=str(tmp_path))
        salvar_export(sessao_b, df_exemplo, "b.csv", pasta_base=str(tmp_path))

        assert sessao_a["_scouting_sessao_id"] != sessao_b["_scouting_sessao_id"]


class TestListarExports:
    def test_lista_do_mais_recente_para_o_mais_antigo(self, tmp_path, df_exemplo):
        sessao = {}
        salvar_export(sessao, df_exemplo, "primeiro.csv", pasta_base=str(tmp_path))
        salvar_export(sessao, df_exemplo, "segundo.csv", pasta_base=str(tmp_path))
        salvar_export(sessao, df_exemplo, "terceiro.csv", pasta_base=str(tmp_path))

        exports = listar_exports(sessao, pasta_base=str(tmp_path))

        nomes = [export["nome_arquivo"] for export in exports]
        assert nomes == ["terceiro.csv", "segundo.csv", "primeiro.csv"]

    def test_metadata_inclui_quantidade_de_jogadores(self, tmp_path, df_exemplo):
        sessao = {}
        salvar_export(sessao, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        exports = listar_exports(sessao, pasta_base=str(tmp_path))

        assert exports[0]["num_jogadores"] == len(df_exemplo)


class TestLimiteDeExportsPorSessao:
    def test_ultrapassar_o_limite_apaga_o_mais_antigo(self, tmp_path, df_exemplo):
        sessao = {}
        for i in range(MAX_EXPORTS_POR_SESSAO + 3):
            salvar_export(sessao, df_exemplo, f"export_{i}.csv", pasta_base=str(tmp_path))

        exports = listar_exports(sessao, pasta_base=str(tmp_path))

        assert len(exports) == MAX_EXPORTS_POR_SESSAO
        # Os 3 primeiros (export_0, export_1, export_2) devem ter sido
        # descartados; o mais recente da lista deve ser o último salvo.
        nomes = {export["nome_arquivo"] for export in exports}
        assert "export_0.csv" not in nomes
        assert f"export_{MAX_EXPORTS_POR_SESSAO + 2}.csv" in nomes


class TestSessaoDeUsuarioLogado:
    """Cobre a Fase 6, item 21: uma vez logado, os dados passam a ficar
    numa pasta permanente atrelada à conta, em vez do UUID aleatório por
    navegador."""

    def test_usuario_logado_usa_pasta_deterministica(self, tmp_path, df_exemplo):
        sessao = {CHAVE_USUARIO_ID: 42}

        export_id = salvar_export(sessao, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        assert (tmp_path / "usr_42" / f"{export_id}.pkl").exists()
        # E não deveria ter criado nenhum UUID aleatório de sessão anônima:
        assert CHAVE_ID_SESSAO not in sessao

    def test_duas_abas_da_mesma_conta_compartilham_os_dados(self, tmp_path, df_exemplo):
        # Simula duas "sessões" (ex: dois navegadores) da MESMA conta
        # logada: precisam enxergar os mesmos exports.
        sessao_aba_1 = {CHAVE_USUARIO_ID: 42}
        sessao_aba_2 = {CHAVE_USUARIO_ID: 42}

        salvar_export(sessao_aba_1, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        df_pela_aba_2 = carregar_df_atual(sessao_aba_2, pasta_base=str(tmp_path))
        pd.testing.assert_frame_equal(df_pela_aba_2, df_exemplo)


class TestAdotarSessaoAnonima:
    """Cobre a Fase 6, item 21: primeiro login aproveita os dados que já
    tinham sido enviados de forma anônima, em vez de perdê-los."""

    def test_adota_a_pasta_anonima_para_a_conta(self, tmp_path, df_exemplo):
        sessao = {}
        export_id = salvar_export(sessao, df_exemplo, "export.csv", pasta_base=str(tmp_path))

        adotar_sessao_anonima(sessao, usuario_id=42, pasta_base=str(tmp_path))
        sessao[CHAVE_USUARIO_ID] = 42

        # O export enviado antes do login continua acessível, agora pela
        # pasta da conta.
        df_carregado = carregar_export(sessao, export_id, pasta_base=str(tmp_path))
        pd.testing.assert_frame_equal(df_carregado, df_exemplo)

    def test_nao_faz_nada_se_sessao_anonima_nunca_enviou_nada(self, tmp_path):
        sessao = {}
        # Não deveria lançar exceção nenhuma.
        adotar_sessao_anonima(sessao, usuario_id=42, pasta_base=str(tmp_path))
        assert not (tmp_path / "usr_42").exists()

    def test_nao_sobrescreve_conta_que_ja_tem_dados_proprios(self, tmp_path, df_exemplo):
        # A conta já logou antes (de outro navegador) e já tem um export.
        sessao_conta_existente = {CHAVE_USUARIO_ID: 42}
        salvar_export(sessao_conta_existente, df_exemplo, "export_da_conta.csv", pasta_base=str(tmp_path))

        # Um navegador novo, anônimo, também tinha enviado algo.
        sessao_anonima_nova = {}
        salvar_export(sessao_anonima_nova, df_exemplo, "export_anonimo.csv", pasta_base=str(tmp_path))

        adotar_sessao_anonima(sessao_anonima_nova, usuario_id=42, pasta_base=str(tmp_path))
        sessao_anonima_nova[CHAVE_USUARIO_ID] = 42

        # Os dados da conta (já existentes) continuam sendo os que valem.
        exports = listar_exports(sessao_anonima_nova, pasta_base=str(tmp_path))
        nomes = {export["nome_arquivo"] for export in exports}
        assert nomes == {"export_da_conta.csv"}
