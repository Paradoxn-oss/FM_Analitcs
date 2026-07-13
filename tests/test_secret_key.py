"""
Testes para o fallback de app.secret_key quando FLASK_SECRET_KEY não está
definida no ambiente.

Contexto do bug que estes testes cobrem: antes, sem essa variável, o app
sorteava uma chave nova (`secrets.token_hex(32)`) a cada import/restart do
processo. Como o cookie de sessão (usado por scouting/sessao.py para achar
o elenco.pkl salvo via /elenco/upload) é assinado com essa chave, trocar a
chave invalida todos os cookies existentes — na prática, o usuário perdia
o acesso ao elenco (e ao export) já enviados, como se nunca tivesse
enviado nada. A correção persiste a chave em disco (ARQUIVO_SECRET_KEY) e
reaproveita o mesmo valor entre execuções.
"""

import pytest

import app as app_module


@pytest.fixture
def arquivo_chave_isolado(tmp_path, monkeypatch):
    """Aponta ARQUIVO_SECRET_KEY para dentro de tmp_path (em vez do
    arquivo real do projeto) e garante que FLASK_SECRET_KEY não está
    definida no ambiente do teste — sem isso, os testes tocariam o
    `.flask_secret_key` real do repositório e/ou herdariam a variável
    fixa definida em conftest.py para os demais testes.
    """
    caminho = tmp_path / ".flask_secret_key"
    monkeypatch.setattr(app_module, "ARQUIVO_SECRET_KEY", str(caminho))
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    return caminho


class TestObterSecretKey:
    def test_usa_variavel_de_ambiente_quando_definida(self, arquivo_chave_isolado, monkeypatch):
        monkeypatch.setenv("FLASK_SECRET_KEY", "chave-do-ambiente")

        chave = app_module._obter_secret_key()

        assert chave == "chave-do-ambiente"
        # Com a variável definida, o fallback em disco nem deveria ser
        # tocado.
        assert not arquivo_chave_isolado.exists()

    def test_gera_e_persiste_quando_nao_ha_variavel_nem_arquivo(self, arquivo_chave_isolado):
        chave = app_module._obter_secret_key()

        assert chave
        assert arquivo_chave_isolado.exists()
        assert arquivo_chave_isolado.read_text(encoding="utf-8").strip() == chave

    def test_reaproveita_chave_ja_salva_em_disco(self, arquivo_chave_isolado):
        arquivo_chave_isolado.write_text("chave-ja-existente", encoding="utf-8")

        assert app_module._obter_secret_key() == "chave-ja-existente"

    def test_chave_persiste_entre_chamadas_sucessivas_sem_arquivo_previo(self, arquivo_chave_isolado):
        """Simula dois "reinícios" seguidos do processo sem
        FLASK_SECRET_KEY definida: a segunda chamada precisa devolver a
        MESMA chave da primeira, em vez de sortear uma nova — é
        exatamente o bug que fazia os dados de /elenco parecerem ter
        sumido a cada reinício.
        """
        primeira_chamada = app_module._obter_secret_key()
        segunda_chamada = app_module._obter_secret_key()

        assert primeira_chamada == segunda_chamada
