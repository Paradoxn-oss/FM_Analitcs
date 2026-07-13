"""
Testes de scouting/parser.py: leitura robusta do arquivo exportado do FM
(detecção de encoding/separador de CSV, validação de extensão, tratamento
de arquivo vazio/malformado).
"""

import pandas as pd
import pytest

from scouting.parser import (
    ArquivoInvalidoError,
    carregar_arquivo,
    carregar_csv,
    detectar_separador,
    extensao_permitida,
)


class TestExtensaoPermitida:
    @pytest.mark.parametrize("nome", ["export.csv", "export.xlsx", "export.xls", "EXPORT.CSV"])
    def test_extensoes_aceitas(self, nome):
        assert extensao_permitida(nome) is True

    @pytest.mark.parametrize("nome", ["export.txt", "export.exe", "export", "export.pdf"])
    def test_extensoes_rejeitadas(self, nome):
        assert extensao_permitida(nome) is False


class TestCarregarCsv:
    def test_le_csv_separado_por_virgula(self, tmp_path):
        caminho = tmp_path / "export.csv"
        caminho.write_text("Jogador,Idade\nFulano,20\nCiclano,25\n", encoding="utf-8")

        df = carregar_csv(str(caminho))

        assert list(df.columns) == ["Jogador", "Idade"]
        assert len(df) == 2

    def test_le_csv_separado_por_ponto_e_virgula(self, tmp_path):
        # Formato mais comum no export do FM em português.
        caminho = tmp_path / "export.csv"
        caminho.write_text("Jogador;Idade\nFulano;20\nCiclano;25\n", encoding="utf-8")

        df = carregar_csv(str(caminho))

        assert list(df.columns) == ["Jogador", "Idade"]
        assert len(df) == 2

    def test_detecta_encoding_latin1(self, tmp_path):
        caminho = tmp_path / "export.csv"
        conteudo = "Jogador;Posição\nJoão;Atacante\n"
        caminho.write_bytes(conteudo.encode("latin-1"))

        df = carregar_csv(str(caminho))

        assert df.iloc[0]["Jogador"] == "João"

    def test_arquivo_vazio_levanta_erro(self, tmp_path):
        caminho = tmp_path / "vazio.csv"
        caminho.write_text("", encoding="utf-8")

        with pytest.raises(ArquivoInvalidoError):
            carregar_csv(str(caminho))

    def test_csv_so_com_cabecalho_levanta_erro_no_carregar_arquivo(self, tmp_path):
        # carregar_csv sozinho não valida "sem linhas de dados" — quem
        # valida isso é carregar_arquivo() (ver teste abaixo).
        caminho = tmp_path / "so_cabecalho.csv"
        caminho.write_text("Jogador,Idade\n", encoding="utf-8")

        with pytest.raises(ArquivoInvalidoError):
            carregar_arquivo(str(caminho))


class TestDetectarSeparador:
    def test_detecta_virgula(self, tmp_path):
        caminho = tmp_path / "a.csv"
        caminho.write_text("A,B,C\n1,2,3\n", encoding="utf-8")
        assert detectar_separador(str(caminho), "utf-8") == ","

    def test_detecta_ponto_e_virgula(self, tmp_path):
        caminho = tmp_path / "a.csv"
        caminho.write_text("A;B;C\n1;2;3\n", encoding="utf-8")
        assert detectar_separador(str(caminho), "utf-8") == ";"

    def test_arquivo_vazio_levanta_erro(self, tmp_path):
        caminho = tmp_path / "a.csv"
        caminho.write_text("", encoding="utf-8")
        with pytest.raises(ArquivoInvalidoError):
            detectar_separador(str(caminho), "utf-8")


class TestCarregarArquivo:
    def test_extensao_nao_suportada_levanta_erro(self, tmp_path):
        caminho = tmp_path / "export.txt"
        caminho.write_text("Jogador,Idade\nFulano,20\n", encoding="utf-8")

        with pytest.raises(ArquivoInvalidoError):
            carregar_arquivo(str(caminho))

    def test_csv_valido_devolve_dataframe(self, tmp_path):
        caminho = tmp_path / "export.csv"
        caminho.write_text("Jogador,Idade\nFulano,20\n", encoding="utf-8")

        df = carregar_arquivo(str(caminho))

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_xlsx_valido_devolve_dataframe(self, tmp_path):
        caminho = tmp_path / "export.xlsx"
        pd.DataFrame({"Jogador": ["Fulano"], "Idade": [20]}).to_excel(str(caminho), index=False)

        df = carregar_arquivo(str(caminho))

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == ["Jogador", "Idade"]
