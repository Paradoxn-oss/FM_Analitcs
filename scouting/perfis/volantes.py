"""
Define os "arquétipos" de volante e os pesos de cada métrica usados por
scouting/ranking.py (calcular_ranking) para gerar a "Nota do Perfil".

Pesos positivos aumentam a nota quanto maior a métrica; pesos negativos
(ex: "Faltas/90": -1) PENALIZAM o jogador quanto maior o valor. Cada chave
aqui vira uma aba de ranking própria na tela de resultado.
"""

PERFIS_VOLANTES = {
    "Volante de Marcação": {
        "Desarmes ganhos/90": 3,
        "% Des Ganhos": 2,
        "Interceptação + Recuperação de bola/90": 3,
        "Eficácia defensiva": 2,
        "Bolas roubadas /90": 2,
        "Faltas/90": -1,
    },
    "Volante Construtor": {
        "% Passes certos": 3,
        "Passes em progressão/90": 3,
        "Passes decisivos / jogos": 2,
        "Criação / 90": 2,
        "Desarmes ganhos/90": 1,
    },
    "Box-to-Box": {
        "Desarmes ganhos/90": 2,
        "% Passes certos": 2,
        "Gols + Ass": 2,
        "Distância /90": 2,
        "Interceptação + Recuperação de bola/90": 1,
        "Criação / 90": 1,
    },
}