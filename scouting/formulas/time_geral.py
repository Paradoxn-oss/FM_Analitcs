"""
Fórmulas de cálculo das métricas do perfil "Time Geral".

Recebe o DataFrame CRU (com as colunas exatamente como o Football Manager
exporta) e devolve um DataFrame com todas as métricas derivadas, seguindo
o mesmo padrão de scouting/formulas/volantes.py.

Fonte: extração automática das fórmulas da planilha `Time_geral.xlsx`
(62 colunas calculadas, 38 colunas de dado bruto). Ao contrário do perfil
"Volante", esta planilha não traz identidade completa do jogador (sem
nação, clube, salário, valor, pé preferido) — é um resumo estatístico
geral do elenco, então só carregamos "Jogador", "Posição" (campo
"Escolhido" do FM) e "Altura" como identidade.

Três particularidades desta planilha em relação a volantes.py:
- As colunas "Chances Criadas em Bola Parada" apareciam DUPLICADAS (mesmo
  nome, colunas BA e BB da planilha original) — renomeadas aqui para
  "Tentativas de Criar chance em Bola Parada" (BA) e "Chances Criadas em
  Bola Parada" (BB), no mesmo padrão de nomenclatura usado no relatório
  de Armadores (que tem a mesma métrica, com esses dois nomes).
- "Nota média" usa 6 como valor padrão quando a nota não pode ser
  convertida (`IFERROR(...,6)` na planilha), diferente de volantes.py
  (que usa 0) — a diferença vem da própria fórmula original, mantida de
  propósito.
- "Desarmes Tentados"/"Desarmes Ganhos": a planilha original somava
  Crt D dentro desses totais; volantes.py trata Crt D como métrica
  separada ("Desarmes Decisivos"), nunca somada aos totais. Unificado
  aqui para bater com volantes.py — ver comentário na seção "Desarme"
  abaixo.
"""

import pandas as pd

from scouting.formulas.util import (
    ColunaAusenteError,
    dividir_seguro,
    numero_br,
    validar_colunas_obrigatorias,
)

# Colunas brutas do FM realmente usadas por alguma fórmula abaixo. A
# planilha original tem 38 colunas brutas ao todo, mas 7 delas (Inf,
# Idade, Pé Preferido, Faltas Contra, PeP, Press. tent., Press. conc.)
# não são usadas por nenhuma fórmula desta aba — omitidas aqui de
# propósito, seguindo o mesmo critério de volantes.py (só exige o que o
# cálculo de fato precisa).
COLUNAS_BRUTAS_OBRIGATORIAS = [
    "Jogador", "Escolhido", "Altura", "Minutos", "Classificação", "Golos",
    "Assist.", "Pens", "Pens M", "Remates", "Rem %", "Cab A", "Cabs",
    "xG", "xA", "Poss Perd/90", "OCG", "Passes Ch", "Cr T", "Cr C",
    "CT-JA", "CC-JA", "Crt D", "Faltas Cometidas", "EPG", "Distância",
    "Fnt", "Pas A", "Ps C", "T Desa", "Des C",
]


def _preencher_texto_vazio(serie, texto_padrao):
    """`=IF(coluna=0, "texto padrão", coluna)` do Excel: troca valores
    vazios/zero (NaN, string vazia, ou o número 0 propriamente dito) pelo
    texto padrão, mantendo o resto como está.
    """
    def _resolver(valor):
        if pd.isna(valor):
            return texto_padrao
        texto = str(valor).strip()
        if texto in ("", "0"):
            return texto_padrao
        return valor

    return serie.apply(_resolver)


def calcular_time_geral(df):
    """Ponto de entrada principal: aplica todas as fórmulas ao DataFrame.

    A ordem do código segue a ordem de DEPENDÊNCIA entre métricas (ex:
    "Ações que geraram finalizações ao gol" usa "Assistências Esperadas
    xA", então esta precisa ser calculada antes) — não necessariamente a
    ordem alfabética das colunas na planilha original, já que o Excel não
    se importa com isso, mas o código precisa.
    """
    validar_colunas_obrigatorias(df, COLUNAS_BRUTAS_OBRIGATORIAS)

    df = df.copy()

    # --- Identidade ---
    df["Jogador"] = _preencher_texto_vazio(df["Jogador"], "Sem Jogador Adicionado")
    df["Posição"] = _preencher_texto_vazio(df["Escolhido"], "VAZIO")
    df["Minutos Jogados"] = df["Minutos"]
    df["Jogos completos"] = df["Minutos Jogados"] / 90
    df["Altura (em metros)"] = numero_br(df["Altura"], sufixo=" cm") / 100

    jogos = df["Jogos completos"]

    # --- Passe ---
    df["Passes Tentados /90"] = dividir_seguro(df["Pas A"], jogos)
    df["Pass Certos / 90"] = dividir_seguro(df["Ps C"], jogos)
    df["Passes errados /90"] = dividir_seguro(df["Pas A"] - df["Ps C"], jogos)
    df["% Passes certos /90"] = dividir_seguro(
        df["Pass Certos / 90"], df["Passes Tentados /90"]
    )
    df["Passes Tentados"] = df["Pas A"]
    df["Passes errados"] = (df["Pas A"] - df["Ps C"]).fillna(0)
    df["% passes errados"] = dividir_seguro(df["Passes errados"], df["Pas A"])

    df["Passes Decisivos"] = df["Passes Ch"]
    df["Pass D / 90"] = dividir_seguro(df["Passes Decisivos"], jogos)

    # --- Falhas ---
    df["Falhas"] = df["EPG"]
    df["Falhas/90"] = dividir_seguro(df["Falhas"], jogos)

    # --- Ações com bola ---
    df["Ações com Bola"] = (
        df["CT-JA"] + df["Remates"] + df["Fnt"] + df["Minutos Jogados"]
    ).fillna(0)
    df["Ações com Bola/90"] = dividir_seguro(df["Ações com Bola"], jogos)

    # --- Posse ---
    df["Perda de posse /90 minutos"] = numero_br(df["Poss Perd/90"])
    df["Perda da posse de bola"] = (
        df["Perda de posse /90 minutos"] * jogos
    ).fillna(0)

    # --- Assistência/gol esperados ---
    df["Assistências Esperadas (xA)"] = pd.to_numeric(df["xA"], errors="coerce").fillna(0)
    df["xA /90"] = dividir_seguro(df["Assistências Esperadas (xA)"], jogos)

    df["xG sem pênalti"] = (
        pd.to_numeric(df["xG"], errors="coerce").fillna(0) - (df["Pens"] * 0.79)
    ).fillna(0)
    df["xG sem pênaltis/90"] = dividir_seguro(df["xG sem pênalti"], jogos)

    df["xA + xG sem pen"] = (
        df["Assistências Esperadas (xA)"] + df["xG sem pênalti"]
    ).fillna(0)
    df["xA + xG sem pen /90"] = dividir_seguro(df["xA + xG sem pen"], jogos)

    # --- Ações que geram finalizações ---
    df["Ações que geraram finalizações ao gol"] = (
        df["OCG"] + df["Assistências Esperadas (xA)"] + df["Rem %"] + df["Golos"]
    ).fillna(0)
    df["Ações que geraram finalizações ao gol /90"] = dividir_seguro(
        df["Ações que geraram finalizações ao gol"], jogos
    )

    # --- Cruzamentos ---
    df["Cruzamentos"] = df["CT-JA"]
    df["Cruzamentos Conseguidos"] = df["CC-JA"]
    df["Cruzamentos %"] = dividir_seguro(df["Cruzamentos Conseguidos"], df["Cruzamentos"])

    # --- Finalizações ---
    df["Finalizações"] = (df["Remates"] - df["Pens"]).fillna(0)
    df["Fin/90"] = dividir_seguro(df["Finalizações"], jogos)

    df["Finalizações Certas /90"] = dividir_seguro(
        df["Rem %"] - df["Pens M"], jogos - df["Pens"]
    )
    df["% Finalizações certas"] = dividir_seguro(
        df["Rem %"] - df["Pens M"], df["Remates"] - df["Pens"]
    )
    df["Conversão de Gols"] = dividir_seguro(
        df["Golos"] - df["Pens M"], df["Remates"] - df["Pens"]
    )

    # --- Gols e assistências ---
    df["Gols"] = df["Golos"]
    df["Gols/90"] = dividir_seguro(df["Gols"], jogos)
    df["Assistências"] = df["Assist."]
    df["Ast/90"] = dividir_seguro(df["Assistências"], jogos)
    df["Gols + Ast"] = (df["Gols"] + df["Assistências"]).fillna(0)
    df["Gols + Ast/90"] = (df["Gols/90"] + df["Ast/90"]).fillna(0)

    # --- Cabeceio ---
    df["Cabeceios Disputados"] = df["Cab A"].fillna(0)
    df["Cabeceios Disputados/90"] = dividir_seguro(df["Cabeceios Disputados"], jogos)
    df["Cabeceios Ganhos"] = df["Cabs"]
    df["Cabs Ganhos / 90"] = dividir_seguro(df["Cabeceios Ganhos"], jogos)
    df["% Cabs"] = dividir_seguro(df["Cabeceios Ganhos"], df["Cabeceios Disputados"])

    # --- Desarme ---
    # A planilha original desta aba somava Crt D ("Desarmes Decisivos",
    # provavelmente cortes/desarmes cruciais do FM) dentro de "Desarmes
    # Tentados" e "Desarmes Ganhos". Isso diverge de volantes.py, que
    # trata Crt D como uma métrica própria e SEPARADA (nunca soma dentro
    # dos totais de tentados/ganhos). Unificado aqui para bater com
    # volantes.py: Crt D vira sua própria coluna "Desarmes Decisivos",
    # e os totais de tentados/ganhos ficam só com T Desa/Faltas
    # Cometidas/Des C — sem perder a informação de Crt D, só separando
    # ela corretamente (e agora os dois perfis ficam comparáveis nessas
    # métricas).
    df["Desarmes Tentados"] = (df["T Desa"] + df["Faltas Cometidas"]).fillna(0)
    df["Des T /90"] = dividir_seguro(df["Desarmes Tentados"], jogos)
    df["Desarmes Ganhos"] = df["Des C"].fillna(0)
    df["Desarmes G/90"] = dividir_seguro(df["Desarmes Ganhos"], jogos)
    df["% Desarmes"] = dividir_seguro(df["Desarmes Ganhos"], df["Desarmes Tentados"])

    df["Desarmes Decisivos"] = df["Crt D"]
    df["Desarmes Decisivos / 90"] = dividir_seguro(df["Desarmes Decisivos"], jogos)

    # --- Disciplina ---
    df["Faltas cometidas"] = df["Faltas Cometidas"]
    df["Faltas/90"] = dividir_seguro(df["Faltas cometidas"], jogos)

    # --- Bola parada ---
    # Nomes ajustados em relação à planilha original, que tinha duas
    # colunas chamadas "Chances Criadas em Bola Parada" (BA e BB) — ver
    # docstring do módulo.
    df["Tentativas de Criar chance em Bola Parada"] = (df["Cr T"] - df["CT-JA"]).fillna(0)
    df["Chances Criadas em Bola Parada"] = (df["Cr C"] - df["CC-JA"]).fillna(0)
    df["% Aproveitamento das Tentativas de Criar chance em BP"] = dividir_seguro(
        df["Chances Criadas em Bola Parada"], df["Tentativas de Criar chance em Bola Parada"]
    )

    # --- Físico ---
    df["Distância Percorrida"] = numero_br(df["Distância"], sufixo=" km")
    df["Dist / 90"] = dividir_seguro(df["Distância Percorrida"], jogos)
    df["Fintas"] = df["Fnt"]
    df["Fintas/90"] = dividir_seguro(df["Fintas"], jogos)

    # --- Avaliação ---
    # Diferente de numero_br (que sempre usa 0 como padrão), a fórmula
    # original usa 6 quando a nota não pode ser convertida — mantido de
    # propósito (ver docstring do módulo).
    notas = df["Classificação"].astype(str).str.replace(",", ".", regex=False)
    df["Nota média"] = pd.to_numeric(notas, errors="coerce").fillna(6)

    return df
