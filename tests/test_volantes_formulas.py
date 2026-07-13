"""
Testes de scouting/formulas/volantes.py (calcular_volantes): a
transformação das colunas cruas do export do FM nas métricas calculadas
que aparecem nas tabelas da tela de resultado.
"""

import pandas as pd
import pytest

from scouting.formulas.util import ColunaAusenteError
from scouting.formulas.volantes import calcular_volantes


class TestCalcularVolantesMetricasBasicas:
    def test_jogos_completos_a_partir_dos_minutos(self, df_volantes_calculado):
        # Jogador Ofensivo: 1800 minutos / 90 = 20 jogos completos.
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Jogos Completos"] == 20.0

    def test_gols_e_assistencias_somados(self, df_volantes_calculado):
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Gols"] == 10
        assert linha["Assistências"] == 8
        assert linha["Gols + Ass"] == 18

    def test_percentual_passes_certos(self, df_volantes_calculado):
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        # 700 certos de 800 tentados = 0.875
        assert linha["% Passes certos"] == pytest.approx(0.875)

    def test_presencas_titular_e_banco(self, df_volantes_calculado):
        # "20 (2)" -> 20 titular + 2 banco = 22 jogos totais
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Jogos Totais"] == 22

    def test_presencas_formato_inesperado_nao_quebra(self, df_volantes_calculado):
        # "Jogador Reserva" tem Presenças="-" (não bate com "N (M)" nem é
        # um número puro) -> deve virar (0, 0) em vez de lançar exceção.
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Reserva"]
        assert linha["Jogos Totais"] == 0

    def test_altura_convertida_para_metros(self, df_volantes_calculado):
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Altura"] == pytest.approx(1.80)

    def test_data_final_contrato_sem_data_vira_texto_amigavel(self, df_volantes_calculado):
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Defensivo"]
        assert linha["Data Final de Contrato"] == "Sem Data Final"

    def test_data_final_contrato_com_data_mantida(self, df_volantes_calculado):
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Ofensivo"]
        assert linha["Data Final de Contrato"] == "30/06/2027"


class TestCalcularVolantesJogadorComZeroMinutos:
    """Regressão: um jogador com 0 minutos jogados (nunca entrou em campo)
    não pode gerar inf/NaN em nenhuma métrica "/90" — todas devem cair
    para 0 (o default de dividir_seguro), como qualquer outra divisão por
    zero no restante do app.
    """

    def test_metricas_por_90_nao_viram_infinito_ou_nan(self, df_volantes_calculado):
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Reserva"]
        colunas_por_90 = [
            "Pass C / 90", "Faltas/90", "Mov Press T/90", "Desarmes ganhos/90",
            "Cabs Disputados /90", "Bolas int/90", "Distância /90",
        ]
        for coluna in colunas_por_90:
            valor = linha[coluna]
            assert pd.notna(valor), f"{coluna} não deveria ser NaN"
            assert valor not in (float("inf"), float("-inf")), f"{coluna} não deveria ser infinito"
            assert valor == 0.0

    def test_jogos_como_titular_usa_default_100_por_cento(self, df_volantes_calculado):
        # dividir_seguro(0, 0, default=1.0) -> 1.0 -> * 100 = 100.0, em vez
        # de 0% (o que sugeriria erroneamente que o jogador nunca é titular).
        linha = df_volantes_calculado.set_index("Jogador").loc["Jogador Reserva"]
        assert linha["Jogos como Titular"] == 100.0


class TestCalcularVolantesValidacao:
    def test_falta_coluna_obrigatoria_levanta_erro_claro(self, df_fm_bruto):
        df_incompleto = df_fm_bruto.drop(columns=["Golos"])
        with pytest.raises(ColunaAusenteError) as excinfo:
            calcular_volantes(df_incompleto)
        assert "Golos" in str(excinfo.value)

    def test_nao_modifica_o_dataframe_original(self, df_fm_bruto):
        # calcular_volantes faz df.copy() logo no início — o DataFrame que
        # o chamador passou não deve ganhar as colunas novas.
        colunas_antes = set(df_fm_bruto.columns)
        calcular_volantes(df_fm_bruto)
        assert set(df_fm_bruto.columns) == colunas_antes

