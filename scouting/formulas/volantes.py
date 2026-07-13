"""
Fórmulas de cálculo das métricas do perfil "Volante".

Recebe o DataFrame CRU (com as colunas exatamente como o Football Manager
exporta, ex: "Golos", "Ps C", "Cab A") e devolve um DataFrame com todas as
métricas derivadas (por 90 minutos, percentuais, agregados) que aparecem
nas tabelas da tela de resultado — ver scouting/colunas/volantes.py para
saber quais colunas vão em qual aba.
"""

import re
import pandas as pd

from scouting.formulas.util import (
    ColunaAusenteError,
    dividir_seguro,
    numero_br,
    validar_colunas_obrigatorias,
)

# Todas as colunas que o arquivo do FM PRECISA ter para o cálculo funcionar.
# Se alguma faltar, o usuário recebe um erro claro dizendo qual, em vez de
# um KeyError genérico lá no meio do processamento.
COLUNAS_BRUTAS_OBRIGATORIAS = [
    "Jogador", "Nação", "Pé Preferido", "Clube", "Idade", "Salário",
    "Valor Estimado", "Altura", "Expira", "Minutos", "Presenças",
    "Golos", "Assist.", "HdJ", "Pens", "Pens M", "Amr", "Cartões vermelhos",
    "Faltas Cometidas", "Press. tent.", "Press. conc.", "Cab A", "T Desa",
    "Cabs", "Des C", "Crt D", "Pas A", "Ps C", "PeP", "Passes Ch", "Crt",
    "Blq", "Rems Bloq", "Alívios", "Cab Dec/90", "xA", "OCG", "Distância",
    "Poss Con/90", "Poss Perd/90", "Remates", "Rem %", "Classificação", "EPG",
]


def _extrair_titular_banco(valor):
    """O FM exporta a coluna "Presenças" no formato "20 (2)", onde 20 é o
    número de jogos como titular e 2 (entre parênteses) é como reserva.
    Esta função separa os dois números; se o valor não seguir esse padrão,
    assume que é só o total de titular, com 0 como reserva.
    """
    valor = str(valor).strip()
    match = re.match(r"(\d+)\s*\((\d+)\)", valor)
    if match:
        titular = int(match.group(1))
        banco = int(match.group(2))
        return titular, banco
    try:
        return int(valor), 0
    except ValueError:
        return 0, 0


def calcular_volantes(df):
    """Ponto de entrada principal: aplica todas as fórmulas ao DataFrame.

    Cada bloco `# --- Nome ---` abaixo corresponde a um grupo de métricas
    relacionadas que também aparece como uma aba separada na tela de
    resultado (ver COLUNAS_VOLANTES em scouting/colunas/volantes.py).
    """
    validar_colunas_obrigatorias(df, COLUNAS_BRUTAS_OBRIGATORIAS)

    df = df.copy()

    # --- Identidade ---
    # Renomeia/copia colunas do export do FM para os nomes usados na UI.
    df["NAC"] = df["Nação"]
    df["Pé preferido"] = df["Pé Preferido"]
    df["Equipe"] = df["Clube"]
    df["Idade"] = df["Idade"]
    df["Salário"] = df["Salário"]
    df["Valor"] = df["Valor Estimado"]

    # "180 cm" (texto) -> 1.80 (metros, número), mais fácil de ordenar/comparar.
    df["Altura"] = numero_br(df["Altura"], sufixo=" cm") / 100

    # "-" (sem data de expiração) vira um texto amigável em vez de traço solto.
    df["Data Final de Contrato"] = df["Expira"].apply(
        lambda x: "Sem Data Final" if x == "-" else x
    )

    # --- Base de jogos ---
    # "Jogos Completos" é a unidade usada por quase todas as métricas "/90":
    # minutos jogados convertidos em "jogos completos equivalentes"
    # (ex: 990 minutos = 11 jogos completos, mesmo que tenham sido em 15 partidas).
    df["Jogos Completos"] = df["Minutos"] / 90

    titular_banco = df["Presenças"].apply(_extrair_titular_banco)
    df["_titular"] = titular_banco.apply(lambda x: x[0])
    df["_banco"] = titular_banco.apply(lambda x: x[1])

    df["Jogos Totais"] = df["_titular"] + df["_banco"]
    df["Minutos por partida"] = dividir_seguro(df["Minutos"], df["Jogos Totais"])
    # Se "Jogos Totais" for 0 (jogador sem nenhuma presença), assume 100%
    # como titular por padrão (default=1.0 -> vira 100%), em vez de mostrar 0%.
    df["Jogos como Titular"] = dividir_seguro(df["_titular"], df["Jogos Totais"], default=1.0) * 100

    # Colunas auxiliares "_titular"/"_banco" não fazem parte da tabela final.
    df = df.drop(columns=["_titular", "_banco"])

    # --- Ofensivo ---
    df["Gols"] = df["Golos"]
    df["Assistências"] = df["Assist."]
    df["Gols + Ass"] = (df["Gols"] + df["Assistências"]).fillna(0)

    df["Man of the match"] = df["HdJ"]
    df["% de vezes que foi eleito o Homem do Jogo"] = dividir_seguro(
        df["Man of the match"], df["Jogos Completos"]
    )

    # --- Pênaltis ---
    df["Pênaltis batidos"] = df["Pens"]
    df["Pênaltis marcados"] = df["Pens M"]
    df["Pênaltis perdidos"] = (df["Pênaltis batidos"] - df["Pênaltis marcados"]).fillna(0)

    # Jogador sem pênaltis batidos -> 0% de conversão (antes gerava valor "mágico").
    df["% Conversão de pênalti"] = dividir_seguro(
        df["Pênaltis marcados"], df["Pênaltis batidos"]
    )

    # --- Cartões e faltas ---
    df["Amarelos"] = df["Amr"]
    df["Vermelhos"] = df["Cartões vermelhos"]
    df["Total cartões"] = (df["Amarelos"] + df["Vermelhos"]).fillna(0)

    df["Faltas cometidas"] = df["Faltas Cometidas"]
    df["Faltas/90"] = dividir_seguro(df["Faltas cometidas"], df["Jogos Completos"])

    df["Faltas sem cartão"] = (
        df["Faltas cometidas"] - df["Amarelos"] - df["Vermelhos"]
    ).fillna(0)

    df["%Faltas Sem Cartão"] = dividir_seguro(df["Faltas sem cartão"], df["Faltas cometidas"])

    df["Cartões por falta cometida"] = dividir_seguro(df["Total cartões"], df["Faltas cometidas"])

    # --- Movimentos de Pressão ---
    df["Movimentos de pressão tentados"] = df["Press. tent."]
    df["Mov Press T/90"] = dividir_seguro(
        df["Movimentos de pressão tentados"], df["Jogos Completos"]
    )

    df["Movimentos de pressão ganhos"] = df["Press. conc."]
    df["Mov Press Ganhos /90"] = dividir_seguro(
        df["Movimentos de pressão ganhos"], df["Jogos Completos"]
    )

    df["% Pressão ganha/90"] = dividir_seguro(
        df["Movimentos de pressão ganhos"], df["Movimentos de pressão tentados"]
    )

    # --- Bolas disputadas com o adversário ---
    df["Bolas disputadas com o adversário"] = (
        df["Cab A"] + df["T Desa"] + df["Faltas Cometidas"]
    ).fillna(0)

    df["Bolas disputadas com o adversário /90"] = dividir_seguro(
        df["Bolas disputadas com o adversário"], df["Jogos Completos"]
    )

    df["Bolas disputadas e ganhas"] = (
        df["Cabs"] + df["Des C"] + df["Crt D"]
    ).fillna(0)

    df["Bolas disputadas e ganhas /90"] = dividir_seguro(
        df["Bolas disputadas e ganhas"], df["Jogos Completos"]
    )

    df["% Bolas disputadas e ganhas (sem falta)"] = dividir_seguro(
        df["Bolas disputadas e ganhas"], df["Bolas disputadas com o adversário"]
    )

    # --- Passes básicos ---
    df["Passes tentados"] = df["Pas A"]
    df["Passes certos"] = df["Ps C"]

    df["Pass C / 90"] = dividir_seguro(df["Passes certos"], df["Jogos Completos"])

    df["Passes errados"] = (df["Passes tentados"] - df["Passes certos"]).fillna(0)

    df["Passes errados / 90"] = dividir_seguro(df["Passes errados"], df["Jogos Completos"])

    df["% Passes certos"] = dividir_seguro(df["Passes certos"], df["Passes tentados"])

    df["Passes certos  - errados / Jogo"] = dividir_seguro(
        df["Passes certos"] - df["Passes errados"], df["Minutos"] / 90
    )

    # --- Passes curtos vs. progressão ---
    df["Passes que são curtos"] = (df["Pas A"] - df["PeP"]).fillna(0)

    df["Passes curtos certos /90"] = dividir_seguro(
        df["Passes que são curtos"], df["Jogos Completos"]
    )

    df["Passes que são em progressão"] = df["PeP"]

    df["Passes em progressão/90"] = dividir_seguro(
        df["Passes que são em progressão"], df["Jogos Completos"]
    )

    df["% Passes em progressão em relação aos curtos"] = dividir_seguro(
        df["Passes que são em progressão"], df["Passes que são curtos"]
    )

    # --- Passes decisivos ---
    df["Passes decisivos"] = df["Passes Ch"]

    df["Passes decisivos / jogos"] = dividir_seguro(
        df["Passes decisivos"], df["Jogos Completos"]
    )

    # --- Desarmes ---
    df["Desarmes Tentados"] = (df["T Desa"] + df["Faltas Cometidas"]).fillna(0)

    df["Desarmes Tentados/90"] = dividir_seguro(df["Desarmes Tentados"], df["Jogos Completos"])

    df["Desarmes ganhos"] = df["Des C"]

    df["Desarmes ganhos/90"] = dividir_seguro(df["Desarmes ganhos"], df["Jogos Completos"])

    df["Dribles Sofridos"] = (df["T Desa"] - df["Des C"]).fillna(0)

    df["Dribles Sofridos/90"] = dividir_seguro(df["Dribles Sofridos"], df["Jogos Completos"])

    df["% Des Ganhos"] = dividir_seguro(df["Desarmes ganhos"], df["Desarmes Tentados"])

    df["Desarmes Decisivos"] = df["Crt D"]

    df["Desarmes Decisivos / 90"] = dividir_seguro(
        df["Desarmes Decisivos"], df["Jogos Completos"]
    )

    # --- Cabeceios ---
    df["Cabs disputados"] = df["Cab A"]

    df["Cabs Disputados /90"] = dividir_seguro(df["Cabs disputados"], df["Jogos Completos"])

    df["Cabs ganhos"] = df["Cabs"]

    df["Cabs ganhos /90"] = dividir_seguro(df["Cabs ganhos"], df["Jogos Completos"])

    df["% Cabeceios Ganhos"] = dividir_seguro(df["Cabs ganhos"], df["Cabs disputados"])

    df["Cabs perdidos"] = (df["Cab A"] - df["Cabs"]).fillna(0)

    df["Cabs perdidos /90"] = dividir_seguro(df["Cabs perdidos"], df["Jogos Completos"])

    df["Cabs que evitaram jogada ofensiva /90"] = numero_br(df["Cab Dec/90"])

    df["Cabeceios que evitaram jogada ofensiva"] = (
        df["Cabs que evitaram jogada ofensiva /90"] * df["Jogos Completos"]
    ).fillna(0)

    df["% Cabs ganhos"] = dividir_seguro(df["Cabs ganhos"], df["Cabs disputados"])

    # --- Interceptação + Recuperação de bola ---
    df["Interceptação + Recuperação de bola"] = (
        df["Crt"] + df["Blq"] + df["Rems Bloq"] + df["Crt D"]
    ).fillna(0)

    df["Interceptação + Recuperação de bola/90"] = dividir_seguro(
        df["Interceptação + Recuperação de bola"], df["Jogos Completos"]
    )

    soma_desarmes = df["Des C"].sum()
    df["Soma de todos os desarmes"] = soma_desarmes

    # Participação individual do jogador no total de desarmes de toda a base
    # importada (não é "/90", é uma proporção em relação ao grupo inteiro).
    df["% Des em relação a media"] = dividir_seguro(df["Des C"], soma_desarmes)

    # --- Bolas interceptadas e roubadas ---
    df["Bolas interceptadas"] = (
        df["Rems Bloq"] + df["Crt"] + df["Alívios"] + df["Blq"]
    ).fillna(0)

    df["Bolas int/90"] = dividir_seguro(df["Bolas interceptadas"], df["Jogos Completos"])

    df["Bolas roubadas"] = (
        df["Press. conc."] + df["Des C"] + (df["Crt D"] * 0.5)
    ).fillna(0)

    df["Bolas roubadas /90"] = dividir_seguro(df["Bolas roubadas"], df["Jogos Completos"])

    # --- Posse Ganha ---
    df["Posse Ganha/90"] = df["Poss Con/90"]

    # --- Lances defensivos tentados/conseguidos ---
    # "Lances defensivos tentados" é uma métrica agregada e ponderada: cada
    # tipo de ação de risco/erro conta um "peso" diferente (ex: erro grave
    # pesa mais que uma falta comum).
    df["Lances defensivos tentados"] = (
        (df["EPG"] * 3)
        + (df["Amr"] * 1.5)
        + (df["Cartões vermelhos"] * 2)
        + df["T Desa"]
        + df["Crt"]
        + df["Alívios"]
        + df["Blq"]
        + df["Rems Bloq"]
        + df["Faltas Cometidas"]
    ).fillna(0)

    df["Lances DEF tentados / 90"] = dividir_seguro(
        df["Lances defensivos tentados"], df["Jogos Completos"]
    )

    df["Lances defensivos conseguidos"] = (
        df["Des C"]
        + df["Crt"]
        + df["Crt D"]
        + df["Alívios"]
        + df["Blq"]
        + df["Rems Bloq"]
        + (df["Cabeceios que evitaram jogada ofensiva"] * 0.5)
    ).fillna(0)

    df["Lances DEF conseguidos / 90"] = dividir_seguro(
        df["Lances defensivos conseguidos"], df["Jogos Completos"]
    )

    # Eficácia = quantos lances o jogador CONSEGUIU em relação a quantos TENTOU.
    df["Eficácia defensiva"] = dividir_seguro(
        df["Lances defensivos conseguidos"], df["Lances defensivos tentados"]
    )

    # --- Erros Defensivos ---
    df["Erros Defensivos"] = (
        (df["EPG"] * 3)
        + (df["Amr"] * 1.25)
        + (df["Cartões vermelhos"] * 2)
        + df["Faltas Cometidas"]
    ).fillna(0)

    df["Erros Defensivos /90"] = dividir_seguro(df["Erros Defensivos"], df["Jogos Completos"])

    # --- Assistência esperada ---
    df["Assistências Esperadas xA"] = pd.to_numeric(df["xA"], errors="coerce").fillna(0)

    df["xA por passe decisivo"] = dividir_seguro(
        df["Assistências Esperadas xA"], df["Passes decisivos"]
    )

    # --- Criação de jogadas ---
    df["Criação (Jogadas Ofensivas)"] = (df["Passes Ch"] + df["OCG"]).fillna(0)

    df["Criação / 90"] = dividir_seguro(
        df["Criação (Jogadas Ofensivas)"], df["Jogos Completos"]
    )

    # --- Distância e Velocidade ---
    df["Distância percorrida"] = numero_br(df["Distância"], sufixo=" km")
    df["Distância /90"] = dividir_seguro(df["Distância percorrida"], df["Jogos Completos"])

    df["Velocidade Média (em km/h)"] = dividir_seguro(
        (df["Distância percorrida"] * 1000), (df["Minutos"] * 60)
    ) * 3600 / 1000

    # --- Posse Desperdiçada ---
    df["Posse Desperdiçada"] = (
        (df["Pas A"] - df["Ps C"])
        + (df["Cab A"] - df["Cabs"])
        + (df["Remates"] - df["Rem %"])
    ).fillna(0)

    df["Posse Desperdiçada /90"] = dividir_seguro(
        df["Posse Desperdiçada"], df["Jogos Completos"]
    )

    df["Posse perdida /90"] = numero_br(df["Poss Perd/90"])

    # --- Nota média ---
    df["Nota média"] = numero_br(df["Classificação"])

    # DataFrame final: colunas brutas do FM + todas as métricas calculadas
    # acima, prontas para serem filtradas por COLUNAS_VOLANTES em app.py.
    return df
