"""
Leitura do arquivo exportado do Football Manager (CSV ou Excel).

Este módulo cuida só de "abrir o arquivo e devolver um DataFrame pandas cru".
As fórmulas de cálculo (métricas, percentuais, etc.) ficam em
scouting/formulas/volantes.py — este arquivo não sabe nada sobre futebol,
só sobre como ler arquivos de forma robusta.
"""

import os
import csv
import pandas as pd

# Encodings tentados em ordem: a maioria dos exports do FM em português usa
# utf-8 ou cp1252/latin-1, dependendo do sistema operacional do usuário.
ENCODINGS_TENTATIVOS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

# Extensões de arquivo aceitas. Usado tanto aqui (para saber como ler)
# quanto em app.py (para validar o upload ANTES de salvar em disco).
EXTENSOES_PERMITIDAS = {".csv", ".xlsx", ".xls"}


class ArquivoInvalidoError(Exception):
    """Erro para arquivos com formato, encoding ou conteúdo inválido.

    Como ColunaAusenteError (em scouting/formulas/util.py), existe para que
    app.py consiga mostrar uma mensagem amigável em vez de um erro 500 cru.
    """


def extensao_permitida(nome_arquivo):
    """Verifica se a extensão do arquivo está na lista de permitidas.

    IMPORTANTE: isso precisa ser chamado no backend (em app.py) ANTES de
    salvar o arquivo em disco. O atributo `accept=".csv,.xlsx"` do
    <input type="file"> no HTML é só uma sugestão para o navegador — um
    usuário mal-intencionado pode enviar qualquer arquivo (ex: um .exe
    renomeado) ignorando esse atributo completamente.
    """
    extensao = os.path.splitext(nome_arquivo)[1].lower()
    return extensao in EXTENSOES_PERMITIDAS


def detectar_encoding(caminho_arquivo):
    """Tenta abrir o arquivo com cada encoding da lista até um funcionar.

    Necessário porque o FM pode exportar em encodings diferentes dependendo
    do sistema operacional/idioma configurado no jogo do usuário.
    """
    for encoding in ENCODINGS_TENTATIVOS:
        try:
            with open(caminho_arquivo, encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue
    raise ArquivoInvalidoError(
        "Não foi possível detectar o encoding do arquivo. "
        "Tente salvar o CSV como UTF-8."
    )


def detectar_separador(caminho_arquivo, encoding):
    """Descobre se o CSV usa vírgula, ponto e vírgula ou tab como separador,
    usando a primeira linha (cabeçalho) como amostra.
    """
    with open(caminho_arquivo, encoding=encoding) as f:
        amostra = f.readline()

    if not amostra.strip():
        raise ArquivoInvalidoError("O arquivo parece estar vazio.")

    sniffer = csv.Sniffer()
    try:
        dialeto = sniffer.sniff(amostra, delimiters=[",", ";", "\t"])
    except csv.Error:
        raise ArquivoInvalidoError(
            "Não foi possível identificar o separador de colunas do CSV."
        )
    return dialeto.delimiter


def carregar_csv(caminho_arquivo):
    """Lê um CSV detectando automaticamente encoding e separador."""
    encoding = detectar_encoding(caminho_arquivo)
    separador = detectar_separador(caminho_arquivo, encoding)
    try:
        return pd.read_csv(caminho_arquivo, encoding=encoding, sep=separador)
    except pd.errors.ParserError as erro:
        raise ArquivoInvalidoError(f"Erro ao interpretar o CSV: {erro}")


def carregar_xlsx(caminho_arquivo):
    """Lê um arquivo Excel (.xlsx ou .xls)."""
    try:
        return pd.read_excel(caminho_arquivo)
    except ValueError as erro:
        raise ArquivoInvalidoError(f"Erro ao interpretar o Excel: {erro}")


def carregar_arquivo(caminho_arquivo):
    """Ponto de entrada único usado por app.py: detecta a extensão e delega
    para o loader correto (CSV ou Excel), sempre devolvendo um DataFrame
    pandas pronto para as fórmulas de scouting/formulas/volantes.py.
    """
    extensao = os.path.splitext(caminho_arquivo)[1].lower()
    if extensao == ".csv":
        df = carregar_csv(caminho_arquivo)
    elif extensao in (".xlsx", ".xls"):
        df = carregar_xlsx(caminho_arquivo)
    else:
        raise ArquivoInvalidoError(f"Formato não suportado: {extensao}")

    if df.empty:
        raise ArquivoInvalidoError("O arquivo não contém nenhuma linha de dados.")

    return df
