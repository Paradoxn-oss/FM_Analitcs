"""
Define quais colunas (métricas) aparecem em cada aba da tela de resultado
para o perfil "Time Geral" — mesmo padrão de scouting/colunas/volantes.py.

Diferente de Volantes, a "Identidade" aqui é mínima (a planilha de origem
não traz nação, clube, salário, valor ou pé preferido — ver
scouting/formulas/time_geral.py).
"""

COLUNAS_TIME_GERAL = {
    "Identidade": [
        "Jogador", "Posição", "Altura (em metros)",
    ],
    "Volume de Jogo": [
        "Minutos Jogados", "Jogos completos",
    ],
    "Passe": [
        "Passes Tentados", "Passes Tentados /90", "Pass Certos / 90",
        "Passes errados", "Passes errados /90", "% Passes certos /90",
        "% passes errados", "Passes Decisivos", "Pass D / 90",
    ],
    "Falhas": [
        "Falhas", "Falhas/90",
    ],
    "Ações com Bola": [
        "Ações com Bola", "Ações com Bola/90",
    ],
    "Posse": [
        "Perda da posse de bola", "Perda de posse /90 minutos",
    ],
    "Finalização": [
        "Finalizações", "Fin/90", "Finalizações Certas /90",
        "% Finalizações certas", "Conversão de Gols",
    ],
    "Ofensivo": [
        "Gols", "Gols/90", "Assistências", "Ast/90", "Gols + Ast", "Gols + Ast/90",
        "Assistências Esperadas (xA)", "xA /90",
        "xG sem pênalti", "xG sem pênaltis/90",
        "xA + xG sem pen", "xA + xG sem pen /90",
        "Ações que geraram finalizações ao gol", "Ações que geraram finalizações ao gol /90",
    ],
    "Cruzamentos": [
        "Cruzamentos", "Cruzamentos Conseguidos", "Cruzamentos %",
    ],
    "Cabeceio": [
        "Cabeceios Disputados", "Cabeceios Disputados/90",
        "Cabeceios Ganhos", "Cabs Ganhos / 90", "% Cabs",
    ],
    "Desarme": [
        "Desarmes Tentados", "Des T /90", "Desarmes Ganhos", "Desarmes G/90", "% Desarmes",
        "Desarmes Decisivos", "Desarmes Decisivos / 90",
    ],
    "Disciplina": [
        "Faltas cometidas", "Faltas/90",
    ],
    "Bola Parada": [
        "Tentativas de Criar chance em Bola Parada", "Chances Criadas em Bola Parada",
        "% Aproveitamento das Tentativas de Criar chance em BP",
    ],
    "Físico": [
        "Distância Percorrida", "Dist / 90", "Fintas", "Fintas/90",
    ],
    "Avaliação": [
        "Nota média",
    ],
}
