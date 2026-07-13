"""
Modelo de dados — Fase 6, item 23 do ROADMAP_FASE6.md: contas de
usuário, times e temporadas.

Banco: SQLite via Flask-SQLAlchemy (por padrão, `dados/app.db`) —
suficiente para o estágio atual do projeto (baixo volume, um processo por
vez do lado do banco); migra pra Postgres depois sem reescrever nenhum
destes modelos, se o site crescer (só troca a variável de ambiente
DATABASE_URL, ver app.py e DEPLOY.md).

Este módulo substitui o armazenamento de contas que antes vivia em
`dados/usuarios.json` (Fase 6, item 20, implementado só com JSON por
simplicidade) por uma tabela de verdade — exatamente a migração que o
comentário original daquele módulo já previa.

IMPORTANTE (ver README.md / DEPLOY.md): este projeto ainda não usa uma
ferramenta de migração de schema (tipo Alembic/Flask-Migrate) — ao mudar
um destes modelos, é preciso recriar o banco (`db.create_all()` só cria
tabelas que ainda não existem; não altera colunas de tabelas já
existentes). Rode `python scripts/inicializar_banco.py` depois de
qualquer mudança de schema em ambiente de desenvolvimento.
"""

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Usuario(db.Model, UserMixin):
    """Conta logada (login com Google — Fase 6, item 20).

    `UserMixin` já implementa a interface exigida pelo Flask-Login
    (is_authenticated, is_active, is_anonymous, get_id) usando o `id` da
    própria linha — não precisa mais escrever isso à mão (como a versão
    JSON deste módulo fazia).
    """

    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    times = db.relationship(
        "Time",
        backref="usuario",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="Time.criado_em",
    )

    @classmethod
    def obter_ou_criar(cls, google_sub, email, nome):
        """Busca a conta pelo `sub` do Google (identificador único e
        estável da conta Google, que não muda mesmo se o usuário trocar
        de email); cria uma conta nova na primeira vez que essa pessoa
        loga.

        Devolve (usuario, criado_agora) — `criado_agora` é usado por
        app.py/auth_callback pra saber se deve tentar adotar a sessão
        anônima (só faz sentido tentar isso da primeira vez, ver
        scouting/sessao.py::adotar_sessao_anonima).
        """
        usuario = cls.query.filter_by(google_sub=google_sub).first()
        if usuario is not None:
            return usuario, False

        usuario = cls(google_sub=google_sub, email=email, nome=nome or email or "Usuário")
        db.session.add(usuario)
        db.session.commit()
        return usuario, True


class Time(db.Model):
    """Um "time" do usuário (ex: "Botafogo", "meu save da Champions") —
    Fase 6, item 25 ("Meus Times"). Agrupa Temporadas: cada upload de
    export vinculado a esse time fica registrado como uma Temporada
    (item 26)."""

    __tablename__ = "times"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    nome = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    temporadas = db.relationship(
        "Temporada",
        backref="time",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="Temporada.criado_em",
    )

    __table_args__ = (
        db.UniqueConstraint("usuario_id", "nome", name="uq_time_nome_por_usuario"),
    )


class Temporada(db.Model):
    """Um upload de export vinculado a um Time + rótulo de temporada
    (ex: "2025/26") — Fase 6, item 26.

    O DataFrame calculado em si continua em disco como um .pkl (ver
    scouting/sessao.py: salvar_export/carregar_export) — esta tabela só
    guarda QUAL export_id pertence a qual Time+rótulo, não o dado em si.
    Isso evita duplicar toda a lógica de sessao.py, que continua
    funcionando exatamente do jeito que já funcionava.
    """

    __tablename__ = "temporadas"

    id = db.Column(db.Integer, primary_key=True)
    time_id = db.Column(db.Integer, db.ForeignKey("times.id"), nullable=False, index=True)
    rotulo = db.Column(db.String(100), nullable=False)
    export_id = db.Column(db.String(64), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=True)
    num_jogadores = db.Column(db.Integer, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("time_id", "rotulo", name="uq_temporada_rotulo_por_time"),
    )

    @classmethod
    def registrar(cls, time, rotulo, export_id, nome_arquivo, num_jogadores):
        """Cria a Temporada (Time + rótulo) se ainda não existir, ou
        atualiza o export vinculado se já existir — reenviar um arquivo
        pro mesmo Time+rótulo substitui o export anterior daquela
        temporada, em vez de criar uma segunda linha duplicada."""
        temporada = cls.query.filter_by(time_id=time.id, rotulo=rotulo).first()
        if temporada is None:
            temporada = cls(time_id=time.id, rotulo=rotulo)
            db.session.add(temporada)

        temporada.export_id = export_id
        temporada.nome_arquivo = nome_arquivo
        temporada.num_jogadores = num_jogadores
        db.session.commit()
        return temporada


class Scouting(db.Model):
    """Favoritos/notas de jogadores.

    Tabela criada agora junto com o resto do banco (item 23), mas AINDA
    NÃO USADA nesta fase — os favoritos continuam vivendo no
    `localStorage` do navegador (ver static/script.js, obterFavoritos())
    até o item 30 (Bloco D do ROADMAP_FASE6.md) migrar isso pra cá.
    """

    __tablename__ = "scoutings"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    jogador = db.Column(db.String(255), nullable=False)
    time_id = db.Column(db.Integer, db.ForeignKey("times.id"), nullable=True)
    temporada_id = db.Column(db.Integer, db.ForeignKey("temporadas.id"), nullable=True)
    favorito = db.Column(db.Boolean, default=False, nullable=False)
    nota_texto = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
