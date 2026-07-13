"""
Cálculo do ranking por perfil e das "intensidades" usadas para colorir as
células das tabelas (quanto mais forte a cor, melhor o valor do jogador
naquela métrica, em relação aos demais jogadores importados).
"""

import pandas as pd
import numpy as np


class ColunaAusenteError(Exception):
    """Erro para quando um perfil referencia uma coluna que não existe no
    DataFrame (ex: PERFIS_VOLANTES menciona uma métrica com nome errado,
    ou que não foi calculada em scouting/formulas/volantes.py).
    """


def _validar_colunas(df, colunas, contexto=""):
    faltantes = [coluna for coluna in colunas if coluna not in df.columns]
    if faltantes:
        raise ColunaAusenteError(
            f"As colunas {faltantes} não foram encontradas nos dados"
            + (f" ({contexto})" if contexto else "")
            + ". Verifique se o arquivo exportado do Football Manager "
              "contém todos os campos esperados."
        )


def calcular_ranking(df, pesos, nome_perfil=""):
    """Calcula a "Nota do Perfil" (0 a 100) de cada jogador para um perfil
    específico (ex: "Volante de Marcação", com seus pesos definidos em
    scouting/perfis/volantes.py).

    Como funciona:
    1. Cada métrica do perfil é normalizada para uma escala de 0 a 1
       (pior valor do grupo = 0, melhor valor do grupo = 1).
    2. Cada métrica normalizada é multiplicada pelo seu peso (pesos
       negativos penalizam, ex: "Faltas/90": -1).
    3. A soma ponderada é normalizada pela soma dos pesos absolutos e
       multiplicada por 100, virando a "Nota do Perfil" final.

    `nome_perfil` é usado só para deixar a mensagem de erro mais clara
    quando falta alguma coluna (ex: dizer QUAL perfil está com problema).
    """
    _validar_colunas(df, pesos.keys(), contexto=f"perfil '{nome_perfil}'")

    df = df.copy()

    soma_pesos_absolutos = sum(abs(peso) for peso in pesos.values())
    if soma_pesos_absolutos == 0:
        raise ValueError(f"O perfil '{nome_perfil}' não tem pesos válidos (soma zero).")

    nota = pd.Series(0.0, index=df.index)

    for coluna, peso in pesos.items():
        valores = pd.to_numeric(df[coluna], errors="coerce")
        minimo = valores.min()
        maximo = valores.max()

        if pd.isna(minimo) or pd.isna(maximo) or maximo == minimo:
            # Todos os jogadores têm o mesmo valor (ou só há um jogador):
            # não dá pra normalizar por diferença, então usamos 0.5 (neutro)
            # em vez de dividir por zero.
            normalizado = pd.Series(0.5, index=df.index)
        else:
            normalizado = (valores - minimo) / (maximo - minimo)

        nota += normalizado.fillna(0.5) * peso

    df["Nota do Perfil"] = (nota / soma_pesos_absolutos) * 100
    df = df.sort_values("Nota do Perfil", ascending=False)

    return df


def calcular_intensidades(registros, colunas_metricas):
    """Para cada métrica, calcula um valor de 0 a 1 representando a posição
    relativa do jogador (0 = pior do grupo, 1 = melhor do grupo). O template
    (resultado.html) usa esse valor para definir a opacidade da cor de fundo
    de cada célula da tabela — quanto mais intenso, melhor o jogador ali.
    """
    minimos_maximos = {}
    for coluna in colunas_metricas:
        valores = [
            r[coluna] for r in registros
            if coluna in r and isinstance(r[coluna], (int, float)) and not pd.isna(r[coluna])
        ]
        if valores:
            minimos_maximos[coluna] = (min(valores), max(valores))

    intensidades = []
    for registro in registros:
        linha = {}
        for coluna in colunas_metricas:
            valor = registro.get(coluna)
            valor_numerico = (
                isinstance(valor, (int, float)) and not pd.isna(valor)
            )
            if coluna in minimos_maximos and valor_numerico:
                minimo, maximo = minimos_maximos[coluna]
                # Mesmo valor em toda a coluna -> 0.5 (neutro), evita divisão por zero.
                linha[coluna] = 0.5 if maximo == minimo else (valor - minimo) / (maximo - minimo)
            else:
                # None = célula sem cor de fundo (valor não numérico ou ausente).
                linha[coluna] = None
        intensidades.append(linha)

    return intensidades


def calcular_notas_vs_elenco(df_scout, df_elenco, nome_jogador, pesos_por_perfil):
    """Para um jogador escoutado, calcula a "Nota do Perfil" (ver
    calcular_ranking) em cada perfil fixo, mas normalizada em relação ao
    ELENCO do usuário (o "meu time" enviado em /elenco), em vez de em
    relação aos demais jogadores escoutados.

    Como funciona: para cada perfil, junta a linha do jogador escoutado
    com todo o elenco num único grupo e roda calcular_ranking nesse
    grupo — assim a nota do candidato responde exatamente à pergunta
    "se esse jogador entrasse no meu elenco, que nota ele teria comparado
    aos que eu já tenho?".

    Perfis cujas colunas não existam em algum dos dois DataFrames são
    silenciosamente pulados (mesmo comportamento tolerante que o resto do
    app já tem para perfis não aplicáveis a um export específico).

    Devolve uma lista de dicts, um por perfil:
    {"perfil", "nota_jogador", "nota_media_elenco", "nota_melhor_elenco"}
    """
    linha_scout = df_scout[df_scout["Jogador"] == nome_jogador]
    if linha_scout.empty:
        return []

    resultados = []
    for perfil, pesos in pesos_por_perfil.items():
        try:
            grupo = pd.concat([df_elenco, linha_scout], ignore_index=True)
            ranking_grupo = calcular_ranking(grupo, pesos, nome_perfil=perfil)
        except ColunaAusenteError:
            continue

        nota_jogador = float(
            ranking_grupo.loc[ranking_grupo["Jogador"] == nome_jogador, "Nota do Perfil"].iloc[0]
        )
        notas_elenco = ranking_grupo.loc[ranking_grupo["Jogador"] != nome_jogador, "Nota do Perfil"]

        resultados.append({
            "perfil": perfil,
            "nota_jogador": round(nota_jogador, 1),
            "nota_media_elenco": round(float(notas_elenco.mean()), 1) if not notas_elenco.empty else None,
            "nota_melhor_elenco": round(float(notas_elenco.max()), 1) if not notas_elenco.empty else None,
        })

    return resultados


def comparar_metricas_vs_elenco(df_scout, df_elenco, nome_jogador, colunas, jogador_elenco=None):
    """Compara, métrica a métrica, um jogador escoutado com o elenco do
    usuário: ou contra um jogador específico do elenco (`jogador_elenco`
    informado), ou contra a MÉDIA do elenco inteiro (`jogador_elenco=None`).

    Devolve um dict {coluna: {"scout": valor, "comparacao": valor,
    "melhor": "scout" | "comparacao" | "empate" | None}} com valores
    numéricos brutos (a formatação para exibição — %, R$, etc. — é feita
    em app.py, que já tem essa lógica para o restante do dashboard).

    "melhor" vem None para colunas não numéricas (ex: nomes, clubes) —
    o chamador decide como (ou se) exibir essas linhas.
    """
    linha_scout = df_scout[df_scout["Jogador"] == nome_jogador]
    if linha_scout.empty:
        return {}

    linha_scout = linha_scout.iloc[0]

    if jogador_elenco is not None:
        linha_elenco = df_elenco[df_elenco["Jogador"] == jogador_elenco]
        if linha_elenco.empty:
            return {}
        valores_comparacao = linha_elenco.iloc[0]
    else:
        valores_comparacao = df_elenco.mean(numeric_only=True)

    resultado = {}
    for coluna in colunas:
        if coluna not in linha_scout.index:
            continue

        valor_scout = linha_scout[coluna]
        valor_comparacao = valores_comparacao[coluna] if coluna in valores_comparacao.index else None

        scout_numerico = isinstance(valor_scout, (int, float, np.floating, np.integer)) and not pd.isna(valor_scout)
        comparacao_numerica = (
            valor_comparacao is not None
            and isinstance(valor_comparacao, (int, float, np.floating, np.integer))
            and not pd.isna(valor_comparacao)
        )

        melhor = None
        if scout_numerico and comparacao_numerica:
            if valor_scout > valor_comparacao:
                melhor = "scout"
            elif valor_scout < valor_comparacao:
                melhor = "comparacao"
            else:
                melhor = "empate"

        resultado[coluna] = {
            "scout": round(float(valor_scout), 2) if scout_numerico else valor_scout,
            "comparacao": round(float(valor_comparacao), 2) if comparacao_numerica else valor_comparacao,
            "melhor": melhor,
        }

    return resultado


def calcular_similares(df, nome_jogador, colunas_numericas, top_n=8):
    """Encontra os `top_n` jogadores com o perfil estatístico mais parecido
    ao de `nome_jogador`, com base em TODAS as colunas numéricas calculadas
    (não só as de um perfil específico).

    Como funciona:
    1. Cada métrica é normalizada para 0-1 (mesma ideia de calcular_ranking),
       assim métricas em escalas diferentes (ex: "Gols" vs "Distância /90")
       pesam de forma equivalente na comparação.
    2. Calcula a distância euclidiana entre o vetor do jogador de referência
       e o vetor de cada outro jogador — quanto menor a distância, mais
       parecidos são os dois perfis.
    3. Converte a distância em uma "Similaridade" de 0 a 100% (100% = perfil
       idêntico), normalizando pela maior distância encontrada no grupo.

    Retorna sempre uma tupla (nomes, similaridades) — duas listas do mesmo
    tamanho — mesmo quando não há resultado, para que
    `nomes, similaridades = calcular_similares(...)` em app.py nunca quebre
    com "not enough values to unpack".
    """
    dados = df[["Jogador"] + colunas_numericas].copy()

    for coluna in colunas_numericas:
        minimo = dados[coluna].min()
        maximo = dados[coluna].max()
        if maximo == minimo:
            # Todos os jogadores têm o mesmo valor: normaliza para 0.5
            # (neutro) em vez de dividir por zero.
            dados[coluna] = 0.5
        else:
            dados[coluna] = (dados[coluna] - minimo) / (maximo - minimo)

    linha_alvo = dados[dados["Jogador"] == nome_jogador]
    if linha_alvo.empty:
        # Jogador não encontrado (nome inexistente ou digitado errado):
        # devolve duas listas vazias, no mesmo formato do caminho normal.
        return [], []

    vetor_alvo = linha_alvo[colunas_numericas].values[0]
    outros = dados[dados["Jogador"] != nome_jogador].copy()

    distancias = np.sqrt(
        ((outros[colunas_numericas].values - vetor_alvo) ** 2).sum(axis=1)
    )
    distancia_maxima = distancias.max() if len(distancias) > 0 else 1

    outros["Similaridade"] = ((1 - distancias / distancia_maxima) * 100).round(1)
    outros = outros.sort_values("Similaridade", ascending=False).head(top_n)

    return outros["Jogador"].tolist(), outros["Similaridade"].tolist()
