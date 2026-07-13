"""
Testes de scouting/formulas/util.py: dividir_seguro, numero_br,
parse_faixa_monetaria e validar_colunas_obrigatorias.

Vários casos aqui são REGRESSÃO de bugs já corrigidos (ver docstrings das
funções originais) — o objetivo é que, se alguém mexer nessas funções no
futuro e reintroduzir um desses bugs sem querer, o teste quebra e avisa.
"""

import numpy as np
import pandas as pd
import pytest

from scouting.formulas.util import (
    ColunaAusenteError,
    dividir_seguro,
    numero_br,
    parse_faixa_monetaria,
    validar_colunas_obrigatorias,
)


class TestDividirSeguro:
    def test_divisao_normal(self):
        resultado = dividir_seguro(pd.Series([10, 9]), pd.Series([2, 3]))
        assert resultado.tolist() == [5.0, 3.0]

    def test_divisao_por_zero_vira_default_em_vez_de_infinito(self):
        # Regressão: antes da correção, "jogador com 0 minutos jogados"
        # gerava inf/-inf que ia parar direto na tabela/ranking sem aviso.
        resultado = dividir_seguro(pd.Series([10, 5]), pd.Series([2, 0]))
        assert resultado.tolist() == [5.0, 0.0]
        assert not np.isinf(resultado).any()

    def test_divisao_negativa_por_zero_tambem_vira_default(self):
        resultado = dividir_seguro(pd.Series([-10]), pd.Series([0]))
        assert resultado.tolist() == [0.0]

    def test_zero_dividido_por_zero_vira_default(self):
        # 0/0 = NaN (não inf), mas também precisa cair no default.
        resultado = dividir_seguro(pd.Series([0]), pd.Series([0]))
        assert resultado.tolist() == [0.0]

    def test_default_customizado(self):
        resultado = dividir_seguro(pd.Series([1]), pd.Series([0]), default=1.0)
        assert resultado.tolist() == [1.0]

    def test_divisao_por_escalar(self):
        resultado = dividir_seguro(pd.Series([10, 20]), 5)
        assert resultado.tolist() == [2.0, 4.0]


class TestNumeroBr:
    def test_virgula_vira_ponto(self):
        resultado = numero_br(pd.Series(["1,5", "2,75"]))
        assert resultado.tolist() == [1.5, 2.75]

    def test_remove_sufixo(self):
        resultado = numero_br(pd.Series(["120,5 km", "80,0 km"]), sufixo=" km")
        assert resultado.tolist() == [120.5, 80.0]

    def test_valor_invalido_vira_zero_em_vez_de_quebrar(self):
        resultado = numero_br(pd.Series(["abc", "1,5"]))
        assert resultado.tolist() == [0.0, 1.5]

    def test_numero_inteiro_sem_virgula(self):
        resultado = numero_br(pd.Series(["10", "20"]))
        assert resultado.tolist() == [10.0, 20.0]


class TestValidarColunasObrigatorias:
    def test_nao_levanta_erro_quando_todas_presentes(self):
        df = pd.DataFrame({"A": [1], "B": [2]})
        validar_colunas_obrigatorias(df, ["A", "B"])  # não deve lançar

    def test_levanta_erro_com_nome_das_colunas_faltantes(self):
        df = pd.DataFrame({"A": [1]})
        with pytest.raises(ColunaAusenteError) as excinfo:
            validar_colunas_obrigatorias(df, ["A", "B", "C"])
        mensagem = str(excinfo.value)
        assert "['B', 'C']" in mensagem


class TestParseFaixaMonetaria:
    def test_faixa_com_milhoes(self):
        # "R$96M - R$145M" -> média = 120.5M
        resultado = parse_faixa_monetaria(pd.Series(["R$96M - R$145M"]))
        assert resultado.tolist() == [120_500_000.0]

    def test_faixa_com_milhares_e_por_semana(self):
        resultado = parse_faixa_monetaria(pd.Series(["R$96K p/s - R$120K p/s"]))
        assert resultado.tolist() == [108_000.0]

    def test_valor_unico_sem_faixa(self):
        resultado = parse_faixa_monetaria(pd.Series(["R$500 p/s"]))
        assert resultado.tolist() == [500.0]

    def test_texto_sem_numero_vira_zero(self):
        resultado = parse_faixa_monetaria(pd.Series(["Não p/ Venda", "-"]))
        assert resultado.tolist() == [0.0, 0.0]

    def test_decimal_com_ponto_e_sufixo_nao_vira_milhar(self):
        # Regressão: "R$1.5M" já foi tratado (por engano) como "1.500.000
        # sem sufixo" numa versão inicial, virando 15_000_000 em vez de
        # 1_500_000. O ponto aqui é decimal (por causa do sufixo M), não
        # separador de milhar.
        resultado = parse_faixa_monetaria(pd.Series(["R$1.5M"]))
        assert resultado.tolist() == [1_500_000.0]

    def test_decimal_com_virgula_e_sufixo(self):
        resultado = parse_faixa_monetaria(pd.Series(["R$1,5M"]))
        assert resultado.tolist() == [1_500_000.0]

    def test_valor_cheio_com_pontos_de_milhar_sem_sufixo(self):
        # Sem sufixo K/M, o ponto É separador de milhar.
        resultado = parse_faixa_monetaria(pd.Series(["R$1.500.000"]))
        assert resultado.tolist() == [1_500_000.0]

    def test_serie_com_valores_mistos(self):
        serie = pd.Series(["R$10M - R$15M", "Não p/ Venda", "R$500K"])
        resultado = parse_faixa_monetaria(serie)
        assert resultado.tolist() == [12_500_000.0, 0.0, 500_000.0]
