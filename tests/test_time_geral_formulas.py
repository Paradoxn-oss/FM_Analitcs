"""
Testes de scouting/formulas/time_geral.py (calcular_time_geral): a
transformação das colunas cruas da planilha Time_geral.xlsx nas métricas
calculadas, seguindo o mesmo padrão de tests/test_volantes_formulas.py.
"""

import pandas as pd
import pytest

from scouting.formulas.util import ColunaAusenteError
from scouting.formulas.time_geral import calcular_time_geral


class TestCalcularTimeGeralMetricasBasicas:
    def test_jogos_completos_a_partir_dos_minutos(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Jogos completos"] == 10.0

    def test_altura_convertida_para_metros(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Altura (em metros)"] == pytest.approx(1.80)

    def test_passes(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Passes Tentados /90"] == pytest.approx(80)
        assert linha["Pass Certos / 90"] == pytest.approx(70)
        assert linha["Passes errados"] == 100
        assert linha["% Passes certos /90"] == pytest.approx(0.875)
        assert linha["% passes errados"] == pytest.approx(0.125)

    def test_acoes_com_bola(self, df_time_geral_calculado):
        # CT-JA(22) + Remates(40) + Fnt(8) + Minutos Jogados(900) = 970
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Ações com Bola"] == 970
        assert linha["Ações com Bola/90"] == pytest.approx(97)

    def test_perda_de_posse(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Perda de posse /90 minutos"] == pytest.approx(0.8)
        assert linha["Perda da posse de bola"] == pytest.approx(8.0)

    def test_xg_e_xa_sem_penalti(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        # xG(5.5) - Pens(4)*0.79 = 5.5 - 3.16 = 2.34
        assert linha["xG sem pênalti"] == pytest.approx(2.34)
        assert linha["Assistências Esperadas (xA)"] == pytest.approx(3.2)
        assert linha["xA + xG sem pen"] == pytest.approx(5.54)

    def test_finalizacoes_e_conversao(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Finalizações"] == 36  # Remates(40) - Pens(4)
        assert linha["% Finalizações certas"] == pytest.approx(17 / 36)
        assert linha["Conversão de Gols"] == pytest.approx(7 / 36)

    def test_gols_e_assistencias(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Gols"] == 10
        assert linha["Assistências"] == 5
        assert linha["Gols + Ast"] == 15
        assert linha["Gols + Ast/90"] == pytest.approx(1.5)

    def test_cabeceio(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Cabeceios Disputados"] == 20
        assert linha["Cabeceios Ganhos"] == 15
        assert linha["% Cabs"] == pytest.approx(0.75)

    def test_desarme(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        # T Desa(15) + Faltas Cometidas(10) = 25 — Crt D NÃO entra aqui
        # (unificado com volantes.py: Crt D é métrica separada, ver
        # test_desarmes_decisivos abaixo).
        assert linha["Desarmes Tentados"] == 25
        # Des C(10) — idem, sem somar Crt D.
        assert linha["Desarmes Ganhos"] == 10
        assert linha["% Desarmes"] == pytest.approx(10 / 25)

    def test_desarmes_decisivos(self, df_time_geral_calculado):
        # Crt D(5), separado dos totais de tentados/ganhos.
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Desarmes Decisivos"] == 5
        assert linha["Desarmes Decisivos / 90"] == pytest.approx(0.5)

    def test_bola_parada(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        # Cr T(25) - CT-JA(22) = 3 ; Cr C(18) - CC-JA(14) = 4
        assert linha["Tentativas de Criar chance em Bola Parada"] == 3
        assert linha["Chances Criadas em Bola Parada"] == 4
        assert linha["% Aproveitamento das Tentativas de Criar chance em BP"] == pytest.approx(4 / 3)

    def test_fisico(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Distância Percorrida"] == pytest.approx(220.5)
        assert linha["Dist / 90"] == pytest.approx(22.05)
        assert linha["Fintas"] == 8
        assert linha["Fintas/90"] == pytest.approx(0.8)

    def test_nota_media(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Nota média"] == pytest.approx(7.5)


class TestCalcularTimeGeralCamposDeIdentidade:
    def test_posicao_vazia_vira_texto_padrao(self, df_time_geral_calculado):
        # "Jogador Reserva" tem Escolhido=0 -> devia virar "VAZIO", igual
        # à fórmula original =IF(Escolhido=0,"VAZIO",Escolhido).
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Reserva"]
        assert linha["Posição"] == "VAZIO"

    def test_posicao_preenchida_mantida(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Posição"] == "AMC"

    def test_jogador_zero_vira_texto_padrao(self):
        # Cobre a metade da regra de identidade que df_time_geral_bruto não
        # testa (nenhuma linha tem "Jogador"=0, já que ele é usado como
        # índice nos outros testes) — chama calcular_time_geral direto
        # numa linha mínima só pra isso.
        linha_minima = {
            "Jogador": 0, "Escolhido": "DC", "Altura": "180 cm", "Minutos": 90,
            "Classificação": "7,0", "Golos": 0, "Assist.": 0, "Pens": 0, "Pens M": 0,
            "Remates": 0, "Rem %": 0, "Cab A": 0, "Cabs": 0, "xG": 0, "xA": 0,
            "Poss Perd/90": "0", "OCG": 0, "Passes Ch": 0, "Cr T": 0, "Cr C": 0,
            "CT-JA": 0, "CC-JA": 0, "Crt D": 0, "Faltas Cometidas": 0, "EPG": 0,
            "Distância": "0 km", "Fnt": 0, "Pas A": 0, "Ps C": 0, "T Desa": 0, "Des C": 0,
        }
        df = calcular_time_geral(pd.DataFrame([linha_minima]))
        assert df.iloc[0]["Jogador"] == "Sem Jogador Adicionado"


class TestCalcularTimeGeralJogadorComZeroMinutos:
    """Regressão: um jogador com 0 minutos não pode gerar inf/NaN em
    nenhuma métrica "/90" — todas devem cair para 0 (o default de
    dividir_seguro), igual ao que já é garantido para volantes.py.
    """

    def test_metricas_por_90_nao_viram_infinito_ou_nan(self, df_time_geral_calculado):
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Reserva"]
        colunas_por_90 = [
            "Passes Tentados /90", "Falhas/90", "Ações com Bola/90", "xA /90",
            "Fin/90", "Gols/90", "Cabeceios Disputados/90", "Des T /90",
            "Desarmes Decisivos / 90", "Faltas/90", "Dist / 90", "Fintas/90",
        ]
        for coluna in colunas_por_90:
            valor = linha[coluna]
            assert pd.notna(valor), f"{coluna} não deveria ser NaN"
            assert valor not in (float("inf"), float("-inf")), f"{coluna} não deveria ser infinito"
            assert valor == 0.0

    def test_nota_media_usa_default_quando_nao_numerica(self, df_time_geral_calculado):
        # "Jogador Reserva" tem Classificação="-" (não numérico) -> a
        # fórmula original usa 6 como default (IFERROR(...,6)), diferente
        # do 0 usado em volantes.py.
        linha = df_time_geral_calculado.set_index("Jogador").loc["Jogador Reserva"]
        assert linha["Nota média"] == 6.0


class TestCalcularTimeGeralColunaAusente:
    def test_erro_claro_quando_falta_coluna_obrigatoria(self, df_time_geral_bruto):
        df_incompleto = df_time_geral_bruto.drop(columns=["Pas A"])
        with pytest.raises(ColunaAusenteError):
            calcular_time_geral(df_incompleto)
