"""
Cria as tabelas do banco (ver scouting/models.py) se ainda não existirem.

Rode isso manualmente uma vez após o primeiro deploy (ou sempre que
adicionar/mudar um modelo em scouting/models.py — este projeto ainda não
usa uma ferramenta de migração de schema como Alembic, então
`db.create_all()` só cria tabelas novas, não altera colunas de tabelas já
existentes).

Uso (a partir da raiz do projeto, com o venv ativado):
    python scripts/inicializar_banco.py

Em desenvolvimento local, "python app.py" já chama isso sozinho — este
script só é necessário para deploys via gunicorn (ver DEPLOY.md).
"""

import sys

from app import app
from scouting.models import db


def main():
    with app.app_context():
        db.create_all()
    print("Tabelas criadas/conferidas com sucesso (ver dados/app.db ou DATABASE_URL).")


if __name__ == "__main__":
    sys.exit(main())
