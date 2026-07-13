"""
Funções utilitárias usadas pelos módulos de fórmulas (scouting/formulas/*).

Centralizamos aqui duas coisas que se repetiam (e davam problema) em
scouting/formulas/volantes.py:

1. Divisões que podiam gerar `inf`/`-inf` (ex: jogador com 0 minutos jogados).
2. Conversão de números no formato brasileiro ("120,5 km" -> 120.5).
"""

import re

import numpy as np
import pandas as pd


class ColunaAusenteError(Exception):
    """Erro para quando o arquivo importado não contém uma coluna esperada.

    Usamos uma exceção própria (em vez de deixar o KeyError genérico do
    pandas estourar) para que app.py consiga capturar o erro e mostrar uma
    mensagem legível para quem fez o upload, em vez de uma tela de erro 500.
    """


def validar_colunas_obrigatorias(df, colunas):
    """Garante que todas as colunas brutas esperadas do export do FM existem.

    Levanta um erro claro dizendo QUAL coluna falta, em vez de deixar o
    processamento quebrar mais adiante com um KeyError genérico e confuso.
    """
    faltantes = [coluna for coluna in colunas if coluna not in df.columns]
    if faltantes:
        raise ColunaAusenteError(
            "O arquivo enviado não contém as seguintes colunas esperadas: "
            f"{faltantes}. Confira se o export do Football Manager está completo "
            "e no formato correto."
        )


def dividir_seguro(numerador, denominador, default=0.0):
    """Divide duas Series (ou uma Series por um número) tratando divisão por
    zero (inf/-inf) e valores ausentes (NaN).

    Por que isso existe: `pandas.Series.fillna()` NÃO trata infinito, só
    NaN. Uma divisão por zero (ex: jogador com 0 "Jogos Completos", porque
    não entrou em campo) gera `inf`/`-inf`, que passava direto no código
    original e virava um valor absurdo na tabela/ranking, sem nenhum erro
    visível para avisar que algo estava errado.

    Exemplo: dividir_seguro(pd.Series([10, 5]), pd.Series([2, 0]))
             -> [5.0, 0.0]   (em vez de [5.0, inf])
    """
    resultado = numerador / denominador
    resultado = resultado.replace([np.inf, -np.inf], np.nan)
    return resultado.fillna(default)


def numero_br(serie, sufixo=""):
    """Converte uma coluna textual no formato brasileiro para número.

    O FM exporta alguns campos como texto com vírgula decimal e/ou unidade
    junto (ex: "120,5 km", "0,75"). Esta função limpa o sufixo (se houver),
    troca vírgula por ponto, e converte para float — valores que não derem
    para converter viram 0 em vez de quebrar o processamento.
    """
    texto = serie.astype(str)
    if sufixo:
        texto = texto.str.replace(sufixo, "", regex=False)
    texto = texto.str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce").fillna(0)


_PADRAO_VALOR_MONETARIO = re.compile(r"(\d[\d.,]*)\s*([KM])?", re.IGNORECASE)


def _extrair_media_faixa_monetaria(texto):
    """Extrai todos os números de uma faixa monetária (com sufixo opcional
    K/M) e devolve a média. Um único número (sem faixa) devolve ele mesmo.
    Texto sem nenhum número (ex: "Não p/ Venda", "-") devolve 0.
    """
    texto = str(texto).upper()
    valores = []

    for numero, sufixo in _PADRAO_VALOR_MONETARIO.findall(texto):
        # Quando há sufixo K/M, o número é sempre um decimal pequeno (ex:
        # "1.5M", "1,5M"): vírgula/ponto é separador decimal.
        # Sem sufixo, o número é o valor cheio (ex: "1.500.000"): pontos são
        # separadores de milhar e a vírgula (se houver) é o decimal.
        if sufixo:
            numero_limpo = numero.replace(",", ".")
        else:
            numero_limpo = numero.replace(".", "").replace(",", ".")

        try:
            valor = float(numero_limpo)
        except ValueError:
            continue

        if sufixo.upper() == "K":
            valor *= 1_000
        elif sufixo.upper() == "M":
            valor *= 1_000_000

        valores.append(valor)

    if not valores:
        return 0.0
    return sum(valores) / len(valores)


def parse_faixa_monetaria(serie):
    """Converte uma coluna textual de faixa monetária do FM (ex:
    "R$96M - R$145M", "R$96K p/s - R$120K p/s", "R$500 p/s") no valor médio
    numérico da faixa, em Reais (R$) — pronto para ordenar/filtrar/comparar
    numericamente, ao contrário do texto original.

    - Faixas "de-até" (dois números) viram a média dos dois.
    - Um valor único (sem faixa) é usado como está.
    - Textos sem nenhum número (ex: "Não p/ Venda", "-") viram 0.
    """
    return serie.apply(_extrair_media_faixa_monetaria)
