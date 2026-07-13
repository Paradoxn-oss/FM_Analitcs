"""
Define quais colunas (métricas) aparecem em cada aba da tela de resultado
para o perfil "Volante". A chave "Identidade" é tratada de forma especial
em app.py: suas colunas ficam fixas em TODAS as abas (nome, idade, clube...),
enquanto as demais chaves viram uma aba própria na barra lateral.

As métricas aqui precisam existir no DataFrame devolvido por
scouting/formulas/volantes.py (calcular_volantes) — se você adicionar uma
métrica nova lá, lembre de incluir o nome dela aqui também.
"""

COLUNAS_VOLANTES = {
    "Identidade": [
        "Jogador", "NAC", "Pé preferido", "Equipe", "Altura", "Idade",
        "Salário", "Data Final de Contrato", "Valor",
    ],
    "Volume de Jogo": [
        "Jogos Completos", "Jogos Totais", "Minutos por partida", "Jogos como Titular",
    ],
    "Ofensivo": [
        "Gols", "Assistências", "Gols + Ass", "Man of the match",
        "% de vezes que foi eleito o Homem do Jogo",
        "Pênaltis batidos", "Pênaltis marcados", "Pênaltis perdidos", "% Conversão de pênalti",
        "Assistências Esperadas xA", "xA por passe decisivo",
    ],
    "Disciplina": [
        "Amarelos", "Vermelhos", "Total cartões",
        "Faltas cometidas", "Faltas/90", "Faltas sem cartão",
        "%Faltas Sem Cartão", "Cartões por falta cometida",
    ],
    "Pressão": [
        "Movimentos de pressão tentados", "Mov Press T/90",
        "Movimentos de pressão ganhos", "Mov Press Ganhos /90", "% Pressão ganha/90",
    ],
    "Duelos Gerais": [
        "Bolas disputadas com o adversário", "Bolas disputadas com o adversário /90",
        "Bolas disputadas e ganhas", "Bolas disputadas e ganhas /90",
        "% Bolas disputadas e ganhas (sem falta)",
    ],
    "Passe": [
        "Passes tentados", "Passes certos", "Pass C / 90",
        "Passes certos  - errados / Jogo", "Passes errados", "Passes errados / 90",
        "% Passes certos", "Passes que são curtos", "Passes curtos certos /90",
        "Passes que são em progressão", "Passes em progressão/90",
        "% Passes em progressão em relação aos curtos",
        "Passes decisivos", "Passes decisivos / jogos",
    ],
    "Desarme": [
        "Desarmes Tentados", "Desarmes Tentados/90", "Desarmes ganhos", "Desarmes ganhos/90",
        "Dribles Sofridos", "Dribles Sofridos/90", "% Des Ganhos",
        "Desarmes Decisivos", "Desarmes Decisivos / 90",
        "Soma de todos os desarmes", "% Des em relação a media",
    ],
    "Cabeceio": [
        "Cabs disputados", "Cabs Disputados /90", "Cabs ganhos", "Cabs ganhos /90",
        "% Cabeceios Ganhos", "Cabs perdidos", "Cabs perdidos /90",
        "Cabeceios que evitaram jogada ofensiva", "Cabs que evitaram jogada ofensiva /90",
        "% Cabs ganhos",
    ],
    "Recuperação e Interceptação": [
        "Interceptação + Recuperação de bola", "Interceptação + Recuperação de bola/90",
        "Bolas interceptadas", "Bolas int/90", "Bolas roubadas", "Bolas roubadas /90",
        "Posse Ganha/90",
    ],
    "Defensivo Agregado": [
        "Lances defensivos tentados", "Lances DEF tentados / 90",
        "Lances defensivos conseguidos", "Lances DEF conseguidos / 90",
        "Erros Defensivos", "Erros Defensivos /90", "Eficácia defensiva",
    ],
    "Criação de Jogadas": [
        "Criação (Jogadas Ofensivas)", "Criação / 90",
    ],
    "Físico": [
        "Distância percorrida", "Distância /90", "Velocidade Média (em km/h)",
    ],
    "Posse": [
        "Posse Desperdiçada", "Posse Desperdiçada /90", "Posse perdida /90",
    ],
    "Avaliação": [
        "Nota média",
    ],
}