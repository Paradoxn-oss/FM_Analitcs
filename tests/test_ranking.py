"""
Testes de scouting/ranking.py: calcular_ranking (Nota do Perfil),
calcular_intensidades (cor de fundo das células) e calcular_similares
(jogadores parecidos).
"""

import pandas as pd
import pytest

from scouting.ranking import (
    ColunaAusenteError,
    calcular_intensidades,
    calcular_ranking,
    calcular_similares,
)


class TestCalcularRanking:
    def test_jogador_com_melhores_metricas_fica_em_primeiro(self, df_volantes_calculado):
        # "Jogador Ofensivo" tem Gols/Assistências muito acima dos outros
        # dois -> deve liderar um perfil ofensivo simples.
        pesos = {"Gols": 1, "Assistências": 1}
        resultado = calcular_ranking(df_volantes_calculado, pesos, nome_perfil="Ofensivo")
        assert resultado.iloc[0]["Jogador"] == "Jogador Ofensivo"

    def test_resultado_ordenado_por_nota_decrescente(self, df_volantes_calculado):
        pesos = {"Gols": 1}
        resultado = calcular_ranking(df_volantes_calculado, pesos, nome_perfil="Teste")
        notas = resultado["Nota do Perfil"].tolist()
        assert notas == sorted(notas, reverse=True)

    def test_nota_vai_de_0_a_100(self, df_volantes_calculado):
        pesos = {"Gols": 1, "Desarmes ganhos": 1, "Faltas cometidas": -1}
        resultado = calcular_ranking(df_volantes_calculado, pesos, nome_perfil="Teste")
        assert resultado["Nota do Perfil"].between(0, 100).all()

    def test_peso_negativo_penaliza_quem_tem_valor_alto(self, df_volantes_calculado):
        # "Jogador Defensivo" tem MUITO mais faltas cometidas que os outros
        # -> com peso -1 nessa métrica, ele deve ficar em último.
        pesos = {"Faltas cometidas": -1}
        resultado = calcular_ranking(df_volantes_calculado, pesos, nome_perfil="Teste")
        assert resultado.iloc[-1]["Jogador"] == "Jogador Defensivo"

    def test_coluna_ausente_levanta_erro_com_nome_do_perfil(self, df_volantes_calculado):
        pesos = {"Coluna Que Nao Existe": 1}
        with pytest.raises(ColunaAusenteError) as excinfo:
            calcular_ranking(df_volantes_calculado, pesos, nome_perfil="Perfil X")
        assert "Perfil X" in str(excinfo.value)

    def test_soma_de_pesos_zero_levanta_erro(self, df_volantes_calculado):
        # peso 0 -> soma_pesos_absolutos = 0 -> ValueError explícito, em
        # vez de uma divisão por zero silenciosa mais adiante.
        pesos_zero = {"Gols": 0}
        with pytest.raises(ValueError):
            calcular_ranking(df_volantes_calculado, pesos_zero, nome_perfil="Perfil Zero")

    def test_todos_jogadores_com_mesmo_valor_vira_neutro(self):
        # Quando max == min numa métrica, a normalização deve virar 0.5
        # (neutro) em vez de dividir por zero.
        df = pd.DataFrame({
            "Jogador": ["A", "B", "C"],
            "Métrica Igual": [5, 5, 5],
        })
        resultado = calcular_ranking(df, {"Métrica Igual": 1}, nome_perfil="Teste")
        assert resultado["Nota do Perfil"].tolist() == [50.0, 50.0, 50.0]

    def test_nao_modifica_o_dataframe_original(self, df_volantes_calculado):
        colunas_antes = set(df_volantes_calculado.columns)
        calcular_ranking(df_volantes_calculado, {"Gols": 1}, nome_perfil="Teste")
        assert set(df_volantes_calculado.columns) == colunas_antes


class TestCalcularIntensidades:
    def test_melhor_valor_vira_1_pior_vira_0(self):
        registros = [{"Jogador": "A", "Nota": 10}, {"Jogador": "B", "Nota": 0}]
        intensidades = calcular_intensidades(registros, ["Nota"])
        assert intensidades[0]["Nota"] == 1.0
        assert intensidades[1]["Nota"] == 0.0

    def test_valores_iguais_viram_neutro(self):
        registros = [{"Jogador": "A", "Nota": 5}, {"Jogador": "B", "Nota": 5}]
        intensidades = calcular_intensidades(registros, ["Nota"])
        assert intensidades[0]["Nota"] == 0.5
        assert intensidades[1]["Nota"] == 0.5

    def test_valor_nao_numerico_vira_none(self):
        registros = [{"Jogador": "A", "Nota": "texto"}, {"Jogador": "B", "Nota": 5}]
        intensidades = calcular_intensidades(registros, ["Nota"])
        assert intensidades[0]["Nota"] is None

    def test_valor_ausente_vira_none(self):
        registros = [{"Jogador": "A"}, {"Jogador": "B", "Nota": 5}]
        intensidades = calcular_intensidades(registros, ["Nota"])
        assert intensidades[0]["Nota"] is None

    def test_intervalo_sempre_entre_0_e_1(self):
        registros = [{"Jogador": chr(65 + i), "Nota": i * 3.7} for i in range(10)]
        intensidades = calcular_intensidades(registros, ["Nota"])
        for linha in intensidades:
            assert 0.0 <= linha["Nota"] <= 1.0


class TestCalcularSimilares:
    def test_jogador_identico_a_si_mesmo_fica_de_fora_do_resultado(self, df_volantes_calculado):
        colunas_numericas = ["Gols", "Assistências"]
        nomes, _similaridades = calcular_similares(
            df_volantes_calculado, "Jogador Ofensivo", colunas_numericas
        )
        assert "Jogador Ofensivo" not in nomes

    def test_jogador_inexistente_devolve_duas_listas_vazias(self, df_volantes_calculado):
        nomes, similaridades = calcular_similares(
            df_volantes_calculado, "Jogador Que Nao Existe", ["Gols"]
        )
        assert nomes == []
        assert similaridades == []

    def test_similaridade_entre_0_e_100(self, df_volantes_calculado):
        colunas_numericas = ["Gols", "Assistências", "Faltas cometidas"]
        _nomes, similaridades = calcular_similares(
            df_volantes_calculado, "Jogador Ofensivo", colunas_numericas
        )
        for similaridade in similaridades:
            assert 0.0 <= similaridade <= 100.0

    def test_devolve_tuplas_do_mesmo_tamanho(self, df_volantes_calculado):
        nomes, similaridades = calcular_similares(
            df_volantes_calculado, "Jogador Ofensivo", ["Gols", "Assistências"]
        )
        assert len(nomes) == len(similaridades)

    def test_respeita_top_n(self):
        df = pd.DataFrame({
            "Jogador": [f"J{i}" for i in range(10)],
            "Métrica": list(range(10)),
        })
        nomes, _similaridades = calcular_similares(df, "J0", ["Métrica"], top_n=3)
        assert len(nomes) == 3
