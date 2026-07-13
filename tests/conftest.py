"""
Fixtures compartilhadas pelos testes (ver pytest docs: qualquer fixture
definida aqui fica disponível para todos os arquivos test_*.py da pasta
tests/ sem precisar de import).
"""

import os

# Precisa vir ANTES de qualquer teste importar app.py (que lê essa
# variável UMA VEZ, no import do módulo, pra configurar
# SQLALCHEMY_DATABASE_URI — ver app.py). Como conftest.py é sempre
# carregado pelo pytest antes de qualquer arquivo test_*.py, isso garante
# que a suíte inteira usa um banco SQLite em memória, isolado do banco
# real do projeto (dados/app.db) — nunca escreve nada em disco durante os
# testes.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pandas as pd
import pytest

# "import app" (ver tests/test_app.py) roda o módulo inteiro, inclusive
# app.secret_key = _obter_secret_key(). Sem essa variável definida ANTES do
# import, o fallback de app.py escreveria um arquivo .flask_secret_key de
# verdade na raiz do repositório (usando os.path.dirname(__file__), que é
# absoluto e não respeita o chdir para tmp_path feito por
# isola_diretorio_trabalho em test_app.py, já que o import acontece uma
# vez só, na coleta dos testes, antes de qualquer fixture rodar). Definir
# a variável aqui mantém os testes 100% sem efeitos colaterais em disco
# fora de tmp_path, do mesmo jeito que o comportamento anterior (chave
# gerada em memória, sem tocar em arquivo nenhum).
os.environ.setdefault("FLASK_SECRET_KEY", "chave-fixa-para-os-testes-nao-usar-em-producao")


@pytest.fixture
def banco_limpo():
    """Zera o schema do banco (SQLite em memória, ver DATABASE_URL no
    topo deste arquivo) antes do teste, e libera a conexão depois.

    Necessário porque o banco é compartilhado pela sessão de testes
    inteira (uma única engine em memória, reaproveitada entre testes —
    ver scouting/models.py) — sem isso, dados de um teste vazariam pro
    próximo. Usada diretamente por quem testa scouting/models.py, e
    puxada também pela fixture isola_diretorio_trabalho (ver
    tests/test_app.py) para os testes de integração via test_client.
    """
    import app as app_module

    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()

    yield

    with app_module.app.app_context():
        app_module.db.session.remove()


@pytest.fixture
def colunas_brutas_fm():
    """Lista das colunas obrigatórias do export do FM (mesma lista usada
    por scouting/formulas/volantes.py para validar o upload).
    """
    from scouting.formulas.volantes import COLUNAS_BRUTAS_OBRIGATORIAS
    return list(COLUNAS_BRUTAS_OBRIGATORIAS)


@pytest.fixture
def df_fm_bruto():
    """DataFrame "cru" com o formato exato de um export do Football
    Manager (mesmos nomes de coluna, mesmo texto com vírgula decimal,
    faixas monetárias etc) — usado como ponto de partida pela maioria dos
    testes de scouting/formulas e scouting/ranking.

    3 jogadores com perfis propositalmente bem diferentes entre si
    (ofensivo, defensivo, banco/pouco minutado), para que testes de
    ranking/similaridade tenham variação suficiente pra fazer sentido.
    """
    linhas = [
        {
            "Jogador": "Jogador Ofensivo",
            "Nação": "BRA",
            "Pé Preferido": "Direito",
            "Clube": "Clube A",
            "Idade": 24,
            "Salário": "R$50K p/s - R$70K p/s",
            "Valor Estimado": "R$30M - R$45M",
            "Altura": "180 cm",
            "Expira": "30/06/2027",
            "Minutos": 1800,          # 20 jogos completos
            "Presenças": "20 (2)",
            "Golos": 10,
            "Assist.": 8,
            "HdJ": 3,
            "Pens": 4,
            "Pens M": 3,
            "Amr": 2,
            "Cartões vermelhos": 0,
            "Faltas Cometidas": 10,
            "Press. tent.": 100,
            "Press. conc.": 60,
            "Cab A": 20,
            "T Desa": 15,
            "Cabs": 10,
            "Des C": 8,
            "Crt D": 5,
            "Pas A": 800,
            "Ps C": 700,
            "PeP": 200,
            "Passes Ch": 30,
            "Crt": 10,
            "Blq": 5,
            "Rems Bloq": 4,
            "Alívios": 6,
            "Cab Dec/90": "0,3",
            "xA": 6.5,
            "OCG": 12,
            "Distância": "220,5 km",
            "Poss Con/90": 1.5,
            "Poss Perd/90": "0,9",
            "Remates": 40,
            "Rem %": 18,
            "Classificação": "7,4",
            "EPG": 1,
        },
        {
            "Jogador": "Jogador Defensivo",
            "Nação": "ARG",
            "Pé Preferido": "Esquerdo",
            "Clube": "Clube B",
            "Idade": 28,
            "Salário": "R$20K p/s - R$30K p/s",
            "Valor Estimado": "R$8M - R$12M",
            "Altura": "188 cm",
            "Expira": "-",
            "Minutos": 2700,          # 30 jogos completos
            "Presenças": "30 (0)",
            "Golos": 0,
            "Assist.": 1,
            "HdJ": 1,
            "Pens": 0,
            "Pens M": 0,
            "Amr": 8,
            "Cartões vermelhos": 1,
            "Faltas Cometidas": 40,
            "Press. tent.": 220,
            "Press. conc.": 150,
            "Cab A": 90,
            "T Desa": 100,
            "Cabs": 70,
            "Des C": 80,
            "Crt D": 30,
            "Pas A": 1500,
            "Ps C": 1350,
            "PeP": 100,
            "Passes Ch": 5,
            "Crt": 60,
            "Blq": 40,
            "Rems Bloq": 20,
            "Alívios": 90,
            "Cab Dec/90": "1,1",
            "xA": 0.5,
            "OCG": 1,
            "Distância": "330,2 km",
            "Poss Con/90": 0.8,
            "Poss Perd/90": "0,4",
            "Remates": 5,
            "Rem %": 1,
            "Classificação": "6,9",
            "EPG": 4,
        },
        {
            "Jogador": "Jogador Reserva",
            "Nação": "POR",
            "Pé Preferido": "Direito",
            "Clube": "Clube C",
            "Idade": 19,
            "Salário": "Não p/ Venda",
            "Valor Estimado": "-",
            "Altura": "175 cm",
            "Expira": "30/06/2026",
            "Minutos": 0,             # sem minutos jogados: cobre divisão por zero
            "Presenças": "-",         # formato inesperado: deve virar (0, 0)
            "Golos": 0,
            "Assist.": 0,
            "HdJ": 0,
            "Pens": 0,
            "Pens M": 0,
            "Amr": 0,
            "Cartões vermelhos": 0,
            "Faltas Cometidas": 0,
            "Press. tent.": 0,
            "Press. conc.": 0,
            "Cab A": 0,
            "T Desa": 0,
            "Cabs": 0,
            "Des C": 0,
            "Crt D": 0,
            "Pas A": 0,
            "Ps C": 0,
            "PeP": 0,
            "Passes Ch": 0,
            "Crt": 0,
            "Blq": 0,
            "Rems Bloq": 0,
            "Alívios": 0,
            "Cab Dec/90": "0",
            "xA": 0,
            "OCG": 0,
            "Distância": "0 km",
            "Poss Con/90": 0,
            "Poss Perd/90": "0",
            "Remates": 0,
            "Rem %": 0,
            "Classificação": "0",
            "EPG": 0,
        },
    ]
    return pd.DataFrame(linhas)


@pytest.fixture
def df_volantes_calculado(df_fm_bruto):
    """df_fm_bruto já processado por calcular_volantes() — usado pelos
    testes de scouting/ranking.py, que operam sobre as métricas calculadas
    (não sobre as colunas cruas do FM).
    """
    from scouting.formulas.volantes import calcular_volantes
    return calcular_volantes(df_fm_bruto)


@pytest.fixture
def df_time_geral_bruto():
    """DataFrame "cru" no formato da planilha Time_geral.xlsx (colunas
    diferentes de df_fm_bruto: sem nação/clube/salário/valor, com
    "Escolhido" no lugar de posição). 3 jogadores: um com estatísticas
    variadas (pra conferir os cálculos), um com 0 minutos e valores
    "vazios" (pra conferir os defaults de divisão por zero e dos campos
    de identidade), e um com Classificação não numérica (pra conferir o
    default de "Nota média").
    """
    linhas = [
        {
            "Jogador": "Jogador Ofensivo",
            "Escolhido": "AMC",
            "Altura": "180 cm",
            "Minutos": 900,
            "Classificação": "7,50",
            "Golos": 10,
            "Assist.": 5,
            "Pens": 4,
            "Pens M": 3,
            "Remates": 40,
            "Rem %": 20,
            "Cab A": 20,
            "Cabs": 15,
            "xG": "5.5",
            "xA": "3.2",
            "Poss Perd/90": "0,8",
            "OCG": 12,
            "Passes Ch": 30,
            "Cr T": 25,
            "Cr C": 18,
            "CT-JA": 22,
            "CC-JA": 14,
            "Crt D": 5,
            "Faltas Cometidas": 10,
            "EPG": 3,
            "Distância": "220,5 km",
            "Fnt": 8,
            "Pas A": 800,
            "Ps C": 700,
            "T Desa": 15,
            "Des C": 10,
        },
        {
            "Jogador": "Jogador Reserva",
            "Escolhido": 0,
            "Altura": "175 cm",
            "Minutos": 0,
            "Classificação": "-",
            "Golos": 0,
            "Assist.": 0,
            "Pens": 0,
            "Pens M": 0,
            "Remates": 0,
            "Rem %": 0,
            "Cab A": 0,
            "Cabs": 0,
            "xG": 0,
            "xA": 0,
            "Poss Perd/90": "0",
            "OCG": 0,
            "Passes Ch": 0,
            "Cr T": 0,
            "Cr C": 0,
            "CT-JA": 0,
            "CC-JA": 0,
            "Crt D": 0,
            "Faltas Cometidas": 0,
            "EPG": 0,
            "Distância": "0 km",
            "Fnt": 0,
            "Pas A": 0,
            "Ps C": 0,
            "T Desa": 0,
            "Des C": 0,
        },
    ]
    return pd.DataFrame(linhas)


@pytest.fixture
def df_time_geral_calculado(df_time_geral_bruto):
    """df_time_geral_bruto já processado por calcular_time_geral()."""
    from scouting.formulas.time_geral import calcular_time_geral
    return calcular_time_geral(df_time_geral_bruto)
