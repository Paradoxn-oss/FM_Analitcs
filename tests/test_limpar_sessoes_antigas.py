"""
Testes de scripts/limpar_sessoes_antigas.py (item 2 da Fase 1 do roadmap:
limpeza por idade em session_cache/, já que o limite existente em
scouting/sessao.py é só por QUANTIDADE de exports dentro de uma mesma
sessão, não por sessões abandonadas).
"""

import os
import time

import pytest

from scripts.limpar_sessoes_antigas import (
    encontrar_sessoes_antigas,
    limpar_sessoes_antigas,
)

DIA_EM_SEGUNDOS = 86400


def _criar_sessao(pasta_base, nome, idade_em_dias):
    """Cria uma pasta de sessão fake com um metadata.json cujo mtime foi
    "voltado no tempo" para simular uma sessão antiga.
    """
    pasta_sessao = pasta_base / nome
    pasta_sessao.mkdir()
    arquivo = pasta_sessao / "metadata.json"
    arquivo.write_text("[]", encoding="utf-8")

    mtime_alvo = time.time() - (idade_em_dias * DIA_EM_SEGUNDOS)
    os.utime(arquivo, (mtime_alvo, mtime_alvo))
    return pasta_sessao


class TestEncontrarSessoesAntigas:
    def test_sessao_recente_nao_e_encontrada(self, tmp_path):
        _criar_sessao(tmp_path, "sessao_recente", idade_em_dias=1)

        antigas = encontrar_sessoes_antigas(pasta_base=str(tmp_path), dias=30)

        assert antigas == []

    def test_sessao_antiga_e_encontrada(self, tmp_path):
        pasta_antiga = _criar_sessao(tmp_path, "sessao_antiga", idade_em_dias=45)

        antigas = encontrar_sessoes_antigas(pasta_base=str(tmp_path), dias=30)

        assert antigas == [str(pasta_antiga)]

    def test_mistura_de_sessoes_antigas_e_recentes(self, tmp_path):
        pasta_antiga = _criar_sessao(tmp_path, "antiga", idade_em_dias=60)
        _criar_sessao(tmp_path, "recente", idade_em_dias=2)

        antigas = encontrar_sessoes_antigas(pasta_base=str(tmp_path), dias=30)

        assert antigas == [str(pasta_antiga)]

    def test_pasta_base_inexistente_devolve_lista_vazia(self, tmp_path):
        pasta_inexistente = tmp_path / "nao_existe"
        assert encontrar_sessoes_antigas(pasta_base=str(pasta_inexistente), dias=30) == []

    def test_pasta_vazia_e_considerada_antiga(self, tmp_path):
        # Sessão sem nenhum arquivo dentro (ex: falha no meio de um
        # salvar_export) também deve ser tratada como "abandonada".
        pasta_vazia = tmp_path / "sessao_vazia"
        pasta_vazia.mkdir()

        antigas = encontrar_sessoes_antigas(pasta_base=str(tmp_path), dias=30)

        assert antigas == [str(pasta_vazia)]

    def test_ignora_arquivos_soltos_na_pasta_base(self, tmp_path):
        (tmp_path / "algum_arquivo.txt").write_text("x", encoding="utf-8")

        antigas = encontrar_sessoes_antigas(pasta_base=str(tmp_path), dias=30)

        assert antigas == []


class TestLimparSessoesAntigas:
    def test_dry_run_nao_apaga_nada(self, tmp_path):
        pasta_antiga = _criar_sessao(tmp_path, "antiga", idade_em_dias=60)

        apagadas = limpar_sessoes_antigas(pasta_base=str(tmp_path), dias=30, dry_run=True)

        assert apagadas == [str(pasta_antiga)]
        assert pasta_antiga.exists()

    def test_apaga_de_fato_sem_dry_run(self, tmp_path):
        pasta_antiga = _criar_sessao(tmp_path, "antiga", idade_em_dias=60)
        pasta_recente = _criar_sessao(tmp_path, "recente", idade_em_dias=1)

        apagadas = limpar_sessoes_antigas(pasta_base=str(tmp_path), dias=30, dry_run=False)

        assert apagadas == [str(pasta_antiga)]
        assert not pasta_antiga.exists()
        assert pasta_recente.exists()
