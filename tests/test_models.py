"""
Testes de scouting/models.py: contas, times e temporadas (Fase 6, item
23 do ROADMAP_FASE6.md).

Todos usam a fixture banco_limpo (ver tests/conftest.py), que reseta o
schema do banco SQLite em memória compartilhado pela suíte antes de cada
teste — necessário porque não há como isolar por tmp_path aqui (ver
comentário em app.py sobre a resolução de caminhos do Flask-SQLAlchemy).
"""

import pytest
from sqlalchemy.exc import IntegrityError

import app as app_module
from scouting.models import Scouting, Temporada, Time, Usuario, db


@pytest.fixture(autouse=True)
def contexto_de_app(banco_limpo):
    """Todos os testes deste arquivo rodam dentro de um app_context (a
    maioria das operações do SQLAlchemy exige isso) e com o schema já
    zerado (banco_limpo)."""
    with app_module.app.app_context():
        yield


class TestUsuarioObterOuCriar:
    def test_primeiro_login_cria_uma_conta_nova(self):
        usuario, criado_agora = Usuario.obter_ou_criar(
            google_sub="sub-123", email="fulano@example.com", nome="Fulano"
        )

        assert criado_agora is True
        assert usuario.id is not None
        assert usuario.google_sub == "sub-123"
        assert usuario.email == "fulano@example.com"
        assert usuario.nome == "Fulano"

    def test_segundo_login_recupera_a_mesma_conta(self):
        primeiro, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")
        segundo, criado_agora = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")

        assert criado_agora is False
        assert segundo.id == primeiro.id

    def test_contas_diferentes_recebem_ids_diferentes(self):
        usuario_a, _ = Usuario.obter_ou_criar("sub-a", "a@example.com", "A")
        usuario_b, _ = Usuario.obter_ou_criar("sub-b", "b@example.com", "B")

        assert usuario_a.id != usuario_b.id

    def test_nome_vazio_usa_email_como_fallback(self):
        usuario, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "")
        assert usuario.nome == "fulano@example.com"

    def test_interface_flask_login(self):
        usuario, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")

        assert usuario.is_authenticated is True
        assert usuario.is_active is True
        assert usuario.is_anonymous is False
        assert usuario.get_id() == str(usuario.id)
        assert isinstance(usuario.get_id(), str)


class TestTime:
    def test_criar_time_para_um_usuario(self):
        usuario, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")

        time = Time(usuario_id=usuario.id, nome="Botafogo")
        db.session.add(time)
        db.session.commit()

        assert time.id is not None
        assert time.usuario.id == usuario.id
        assert usuario.times == [time]

    def test_dois_usuarios_podem_ter_times_com_o_mesmo_nome(self):
        usuario_a, _ = Usuario.obter_ou_criar("sub-a", "a@example.com", "A")
        usuario_b, _ = Usuario.obter_ou_criar("sub-b", "b@example.com", "B")

        db.session.add(Time(usuario_id=usuario_a.id, nome="Botafogo"))
        db.session.add(Time(usuario_id=usuario_b.id, nome="Botafogo"))
        db.session.commit()  # não deveria levantar erro nenhum

        assert Time.query.filter_by(nome="Botafogo").count() == 2

    def test_mesmo_usuario_nao_pode_repetir_nome_de_time(self):
        usuario, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")

        db.session.add(Time(usuario_id=usuario.id, nome="Botafogo"))
        db.session.commit()

        db.session.add(Time(usuario_id=usuario.id, nome="Botafogo"))
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_excluir_time_exclui_temporadas_em_cascata(self):
        usuario, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")
        time = Time(usuario_id=usuario.id, nome="Botafogo")
        db.session.add(time)
        db.session.commit()

        Temporada.registrar(time, "2025/26", export_id="abc123", nome_arquivo="export.csv", num_jogadores=30)
        assert Temporada.query.count() == 1

        db.session.delete(time)
        db.session.commit()

        assert Temporada.query.count() == 0


class TestTemporadaRegistrar:
    @pytest.fixture
    def time_exemplo(self):
        usuario, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")
        time = Time(usuario_id=usuario.id, nome="Botafogo")
        db.session.add(time)
        db.session.commit()
        return time

    def test_cria_uma_temporada_nova(self, time_exemplo):
        temporada = Temporada.registrar(
            time_exemplo, "2025/26", export_id="export-1", nome_arquivo="a.csv", num_jogadores=25
        )

        assert temporada.id is not None
        assert temporada.time_id == time_exemplo.id
        assert temporada.rotulo == "2025/26"
        assert temporada.export_id == "export-1"
        assert temporada.num_jogadores == 25

    def test_reenviar_a_mesma_temporada_atualiza_em_vez_de_duplicar(self, time_exemplo):
        primeira = Temporada.registrar(
            time_exemplo, "2025/26", export_id="export-1", nome_arquivo="a.csv", num_jogadores=25
        )
        segunda = Temporada.registrar(
            time_exemplo, "2025/26", export_id="export-2", nome_arquivo="b.csv", num_jogadores=30
        )

        assert segunda.id == primeira.id  # mesma linha, não uma nova
        assert Temporada.query.filter_by(time_id=time_exemplo.id, rotulo="2025/26").count() == 1
        assert segunda.export_id == "export-2"
        assert segunda.num_jogadores == 30

    def test_rotulos_diferentes_do_mesmo_time_coexistem(self, time_exemplo):
        Temporada.registrar(time_exemplo, "2024/25", export_id="export-1", nome_arquivo="a.csv", num_jogadores=25)
        Temporada.registrar(time_exemplo, "2025/26", export_id="export-2", nome_arquivo="b.csv", num_jogadores=30)

        assert Temporada.query.filter_by(time_id=time_exemplo.id).count() == 2

    def test_time_temporadas_lista_as_temporadas_do_time(self, time_exemplo):
        Temporada.registrar(time_exemplo, "2024/25", export_id="export-1", nome_arquivo="a.csv", num_jogadores=25)
        Temporada.registrar(time_exemplo, "2025/26", export_id="export-2", nome_arquivo="b.csv", num_jogadores=30)

        rotulos = {temporada.rotulo for temporada in time_exemplo.temporadas}
        assert rotulos == {"2024/25", "2025/26"}


class TestScoutingSchema:
    """A tabela de favoritos/notas é criada agora (item 23), mas só passa
    a ser usada de verdade no item 30 (Bloco D) — este teste só confirma
    que o schema básico funciona, sem cobrir nenhuma rota ainda."""

    def test_criar_um_registro_de_scouting(self):
        usuario, _ = Usuario.obter_ou_criar("sub-123", "fulano@example.com", "Fulano")

        scouting = Scouting(usuario_id=usuario.id, jogador="Jogador X", favorito=True, nota_texto="Ótimo passe")
        db.session.add(scouting)
        db.session.commit()

        assert scouting.id is not None
        assert scouting.time_id is None
        assert scouting.temporada_id is None
