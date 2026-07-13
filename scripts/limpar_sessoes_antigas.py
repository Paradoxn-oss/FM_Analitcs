"""
Apaga pastas de sessão abandonadas em session_cache/.

Contexto: cada sessão de navegador ganha sua própria pasta em
session_cache/<id-da-sessao>/ (ver scouting/sessao.py). O único limite
hoje é por QUANTIDADE de exports dentro de uma mesma sessão
(MAX_EXPORTS_POR_SESSAO) — sessões que o usuário nunca mais volta a usar
(cookie expirado, aba fechada, etc.) nunca são apagadas, e a pasta
session_cache/ cresce pra sempre num uso contínuo.

Este script resolve isso por IDADE: apaga toda pasta de sessão cujo
arquivo mais recente (metadata.json OU o .pkl mais novo, o que for mais
recente) não é modificado há mais de N dias.

Uso:
    python scripts/limpar_sessoes_antigas.py                # 30 dias, apaga de fato
    python scripts/limpar_sessoes_antigas.py --dias 7        # janela customizada
    python scripts/limpar_sessoes_antigas.py --dry-run       # só lista, não apaga
    python scripts/limpar_sessoes_antigas.py --pasta outra/  # session_cache/ não-padrão

Equivalente à alternativa de shell puro sugerida no roadmap
(`find session_cache/ -mtime +30 -exec rm -rf {} \\;`), mas:
- funciona igual em qualquer SO (não depende de `find` do GNU coreutils,
  então roda também fora do PythonAnywhere se precisar);
- só considera a pasta como "abandonada" pelo mtime mais recente DENTRO
  dela (não pelo mtime da pasta em si, que alguns filesystems não
  atualizam de forma confiável quando só o conteúdo muda);
- tem --dry-run pra conferir o que seria apagado antes de rodar de
  verdade.

Pensado para ser agendado como Scheduled Task diária no PythonAnywhere
(aba Tasks -> comando:
`python3.x /caminho/do/projeto/scripts/limpar_sessoes_antigas.py`).
"""

import argparse
import os
import shutil
import time

PASTA_BASE_PADRAO = "session_cache"
DIAS_PADRAO = 30


def _mtime_mais_recente(caminho_pasta):
    """mtime do arquivo mais recentemente modificado dentro da pasta (não
    da pasta em si). Devolve None se a pasta estiver vazia.
    """
    mtimes = []
    for nome_arquivo in os.listdir(caminho_pasta):
        caminho_arquivo = os.path.join(caminho_pasta, nome_arquivo)
        if os.path.isfile(caminho_arquivo):
            mtimes.append(os.path.getmtime(caminho_arquivo))
    return max(mtimes) if mtimes else None


def encontrar_sessoes_antigas(pasta_base=PASTA_BASE_PADRAO, dias=DIAS_PADRAO):
    """Devolve a lista de caminhos de pastas de sessão mais antigas que
    `dias` dias (ou sem nenhum arquivo dentro, o que também indica uma
    sessão "morta"/nunca usada de fato).
    """
    if not os.path.isdir(pasta_base):
        return []

    limite = time.time() - (dias * 86400)
    antigas = []

    for nome_sessao in os.listdir(pasta_base):
        caminho_sessao = os.path.join(pasta_base, nome_sessao)
        if not os.path.isdir(caminho_sessao):
            continue

        mtime = _mtime_mais_recente(caminho_sessao)
        if mtime is None or mtime < limite:
            antigas.append(caminho_sessao)

    return antigas


def limpar_sessoes_antigas(pasta_base=PASTA_BASE_PADRAO, dias=DIAS_PADRAO, dry_run=False):
    """Apaga (ou só lista, se dry_run=True) as pastas de sessão antigas.

    Devolve a lista de pastas apagadas (ou que seriam apagadas, em modo
    dry-run).
    """
    antigas = encontrar_sessoes_antigas(pasta_base, dias)

    for caminho_sessao in antigas:
        if dry_run:
            print(f"[dry-run] apagaria: {caminho_sessao}")
        else:
            shutil.rmtree(caminho_sessao, ignore_errors=True)
            print(f"apagado: {caminho_sessao}")

    return antigas


def main():
    parser = argparse.ArgumentParser(
        description="Apaga pastas de sessão abandonadas em session_cache/."
    )
    parser.add_argument(
        "--pasta", default=PASTA_BASE_PADRAO,
        help=f"Pasta base das sessões (padrão: {PASTA_BASE_PADRAO})",
    )
    parser.add_argument(
        "--dias", type=int, default=DIAS_PADRAO,
        help=f"Idade mínima (em dias) para considerar uma sessão abandonada (padrão: {DIAS_PADRAO})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Só lista o que seria apagado, sem apagar de fato.",
    )
    args = parser.parse_args()

    apagadas = limpar_sessoes_antigas(pasta_base=args.pasta, dias=args.dias, dry_run=args.dry_run)

    if not apagadas:
        print("Nenhuma sessão antiga encontrada.")
    else:
        acao = "seriam apagadas" if args.dry_run else "apagadas"
        print(f"\n{len(apagadas)} sessão(ões) {acao}.")


if __name__ == "__main__":
    main()
