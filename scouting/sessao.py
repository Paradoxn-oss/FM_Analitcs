"""
Armazenamento de DataFrames por sessão de usuário (por navegador), em vez
de uma única variável global de processo compartilhada por todo mundo.

Antes, `app.py` guardava o último upload numa variável global (`ultimo_df`):
o upload de uma pessoa "substituía" os dados que outra pessoa estava
analisando, se o app fosse usado por mais de um usuário ao mesmo tempo.

Como funciona agora:
1. Cada sessão de navegador ganha um ID aleatório, guardado no cookie de
   sessão assinado do Flask (não dá pra forjar sem a SECRET_KEY do app).
2. Cada upload processado (já com `calcular_volantes` aplicado) é salvo em
   disco como um arquivo .pkl, dentro de uma pasta exclusiva daquela
   sessão (`session_cache/<id-da-sessao>/`).
3. Um arquivo `metadata.json` na mesma pasta guarda a lista de exports
   feitos naquela sessão (nome do arquivo original, data/hora, quantos
   jogadores). Serve tanto para saber qual é "o último" export (usado
   pelas rotas AJAX: perfil customizado, jogadores parecidos, melhor
   perfil) quanto para listar o histórico de exports da sessão (usado
   pela tela de comparação entre uploads, ver /historico em app.py).
4. Um limite (MAX_EXPORTS_POR_SESSAO) evita que a pasta cresça pra sempre:
   o export mais antigo é apagado quando o limite é ultrapassado.

Login (Fase 6, item 21 do ROADMAP_FASE6.md): quando o visitante loga
(ver app.py, rota /auth/callback), o "ID da sessão" usado pra nomear a
pasta deixa de ser um UUID aleatório por navegador e passa a ser um ID
permanente atrelado à conta (`usr_<id-da-conta>`) — é isso que faz os
dados sobreviverem a trocar de navegador/aparelho depois do login, sem
precisar reescrever `salvar_export`/`carregar_export`/etc: eles continuam
recebendo só um `sessao` (dict-like) e nem percebem se o ID por trás é
anônimo ou de conta. Ver `_id_sessao()` e `adotar_sessao_anonima()`
abaixo.

O parâmetro `sessao` de cada função abaixo aceita qualquer objeto do tipo
dicionário — funciona tanto com `flask.session` de verdade (dentro de uma
requisição) quanto com um dict comum, o que permite testar este módulo
sem precisar de um contexto de requisição Flask (ver tests/test_sessao.py).
"""

import json
import os
import pickle
import re
import uuid
from datetime import datetime

import pandas as pd

PASTA_BASE_PADRAO = "session_cache"

# Formato esperado de um export_id: hex de 32 caracteres (uuid4().hex).
# Usado para validar qualquer export_id que venha de fora (ex: JSON de
# POST /historico/comparar) ANTES de usá-lo para montar um caminho de
# arquivo — sem isso, um valor como "../../outra_sessao/algum_id" viraria
# parte de um os.path.join() e poderia ler o export de outra sessão ou
# qualquer outro arquivo .pkl acessível ao processo (path traversal).
PADRAO_EXPORT_ID = re.compile(r"[0-9a-f]{32}")


def export_id_valido(export_id):
    """True se `export_id` tem o formato esperado (hex de 32 caracteres).

    Usado tanto por app.py (pra devolver 400 cedo, com uma mensagem
    amigável) quanto por carregar_export() abaixo (defesa em profundidade:
    mesmo que algum chamador futuro esqueça de validar antes, a função que
    efetivamente monta o caminho em disco nunca aceita um ID malformado).
    """
    return isinstance(export_id, str) and PADRAO_EXPORT_ID.fullmatch(export_id) is not None

# Quantos exports guardar por sessão antes de começar a apagar os mais
# antigos. Existe só pra não deixar a pasta crescer pra sempre num uso
# contínuo/longo — não é um limite "de negócio".
MAX_EXPORTS_POR_SESSAO = 10

# Chaves usadas dentro do dicionário de sessão (prefixadas para não colidir
# com outras chaves que o Flask ou outra parte do app venham a guardar lá).
CHAVE_ID_SESSAO = "_scouting_sessao_id"
CHAVE_ULTIMO_EXPORT = "_scouting_ultimo_export_id"

# Setada pela rota /auth/callback (ver app.py) no momento do login. Sua
# presença é o que faz _id_sessao() abaixo devolver um ID permanente
# atrelado à conta, em vez do UUID aleatório por navegador.
CHAVE_USUARIO_ID = "_scouting_usuario_id"


def _prefixo_usuario(usuario_id):
    return f"usr_{usuario_id}"


def _id_sessao(sessao):
    """Garante que a sessão tem um ID único (gera um na primeira vez).

    Se a sessão estiver logada (CHAVE_USUARIO_ID presente — ver login em
    app.py), devolve um ID permanente e determinístico atrelado à conta
    em vez de gerar/reaproveitar um UUID aleatório: é assim que os dados
    passam a sobreviver a trocar de navegador ou aparelho depois do
    login, sem precisar duplicar nenhuma lógica de salvar/carregar
    export — muda só QUAL pasta é usada, não COMO ela é usada.
    """
    usuario_id = sessao.get(CHAVE_USUARIO_ID)
    if usuario_id is not None:
        return _prefixo_usuario(usuario_id)

    if CHAVE_ID_SESSAO not in sessao:
        sessao[CHAVE_ID_SESSAO] = uuid.uuid4().hex
    return sessao[CHAVE_ID_SESSAO]


def _tem_identidade(sessao):
    """True se esta sessão já tem uma "identidade" (anônima ou de conta
    logada) — ou seja, se já existe (ou pode existir) uma pasta em
    session_cache/ pra ela. Usado como guarda por carregar_export(),
    listar_exports() etc. para devolver "nada encontrado" cedo, sem
    tentar ler uma pasta que nunca foi criada.

    Repare que checar só CHAVE_ID_SESSAO não bastaria: uma sessão
    logada nunca ganha essa chave (ver _id_sessao acima) — ela usa
    CHAVE_USUARIO_ID diretamente.
    """
    return CHAVE_ID_SESSAO in sessao or CHAVE_USUARIO_ID in sessao


def adotar_sessao_anonima(sessao, usuario_id, pasta_base=PASTA_BASE_PADRAO):
    """Chamada uma única vez, na rota /auth/callback (ver app.py), ANTES
    de gravar CHAVE_USUARIO_ID na sessão.

    Se este navegador já tinha exports/elenco enviados de forma anônima
    antes do login, "adota" essa pasta como sendo da conta que acabou de
    logar — em vez de simplesmente perder o que já tinha sido enviado
    (item 21 do ROADMAP_FASE6.md).

    Não faz nada (e não é um erro) em nenhum destes casos:
    - a sessão anônima nunca enviou nada (não tem o que adotar);
    - a conta já tem uma pasta própria (ex: já logou antes, de outro
      navegador/aparelho) — nesse caso os dados da conta já existente
      têm prioridade; os dados anônimos deste navegador são descartados
      em silêncio, em vez de sobrescrever o que a conta já tinha.
    """
    if CHAVE_ID_SESSAO not in sessao:
        return

    pasta_anonima = os.path.join(pasta_base, sessao[CHAVE_ID_SESSAO])
    if not os.path.isdir(pasta_anonima):
        return

    pasta_usuario = os.path.join(pasta_base, _prefixo_usuario(usuario_id))
    if os.path.exists(pasta_usuario):
        return

    os.rename(pasta_anonima, pasta_usuario)


def _pasta_sessao(sessao, pasta_base=PASTA_BASE_PADRAO):
    pasta = os.path.join(pasta_base, _id_sessao(sessao))
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _caminho_metadata(pasta):
    return os.path.join(pasta, "metadata.json")


def _ler_metadata(pasta):
    caminho = _caminho_metadata(pasta)
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        # metadata corrompido/ilegível: trata como se não houvesse
        # histórico ainda, em vez de derrubar o app inteiro.
        return []


def _escrever_metadata(pasta, exports):
    with open(_caminho_metadata(pasta), "w", encoding="utf-8") as arquivo:
        json.dump(exports, arquivo, ensure_ascii=False, indent=2)


def salvar_export(sessao, df, nome_arquivo, pasta_base=PASTA_BASE_PADRAO):
    """Salva um DataFrame já processado (pós `calcular_volantes`) como um
    novo export desta sessão, e o marca como "o último" — é ele que as
    rotas AJAX (perfil customizado, jogadores parecidos, melhor perfil)
    vão reaproveitar até o próximo upload.

    Devolve o ID do export criado.
    """
    pasta = _pasta_sessao(sessao, pasta_base)
    export_id = uuid.uuid4().hex

    df.to_pickle(os.path.join(pasta, f"{export_id}.pkl"))

    exports = _ler_metadata(pasta)
    exports.append({
        "id": export_id,
        "nome_arquivo": nome_arquivo,
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "num_jogadores": int(len(df)),
    })

    # Mantém só os N exports mais recentes: apaga o(s) mais antigo(s) do
    # disco e da lista, se o limite foi ultrapassado.
    while len(exports) > MAX_EXPORTS_POR_SESSAO:
        mais_antigo = exports.pop(0)
        caminho_antigo = os.path.join(pasta, f"{mais_antigo['id']}.pkl")
        if os.path.exists(caminho_antigo):
            os.remove(caminho_antigo)

    _escrever_metadata(pasta, exports)

    sessao[CHAVE_ULTIMO_EXPORT] = export_id
    return export_id


def carregar_export(sessao, export_id, pasta_base=PASTA_BASE_PADRAO):
    """Carrega um export específico desta sessão pelo ID.

    Devolve None se não existir (ID inválido, export de outra sessão, ou
    arquivo expirado/removido do cache) em vez de lançar uma exceção — o
    chamador decide como avisar o usuário.
    """
    if not _tem_identidade(sessao):
        return None

    # Defesa em profundidade: mesmo que o chamador (ex: uma rota nova em
    # app.py) esqueça de validar o formato antes de chamar esta função,
    # um export_id malformado nunca chega a virar parte de um caminho de
    # arquivo real (ver export_id_valido() acima).
    if not export_id_valido(export_id):
        return None

    pasta = _pasta_sessao(sessao, pasta_base)
    caminho = os.path.join(pasta, f"{export_id}.pkl")
    if not os.path.exists(caminho):
        return None

    try:
        return pd.read_pickle(caminho)
    except (OSError, ValueError, pickle.UnpicklingError):
        return None


def carregar_df_atual(sessao, pasta_base=PASTA_BASE_PADRAO):
    """Carrega o DataFrame do último export desta sessão — usado pelas
    rotas AJAX que reaproveitam o upload mais recente sem exigir um novo
    envio de arquivo.

    Devolve None se esta sessão ainda não fez nenhum upload.
    """
    export_id = sessao.get(CHAVE_ULTIMO_EXPORT)
    if not export_id:
        # CHAVE_ULTIMO_EXPORT vive no cookie desta sessão específica, não
        # na pasta em si — então, para uma conta logada (pasta
        # compartilhada entre navegadores/aparelhos, ver _id_sessao),
        # ela só existe no cookie de QUEM enviou o último export. Se o
        # upload mais recente veio de outro navegador/aparelho da mesma
        # conta, cai aqui: usa o metadata.json da pasta (compartilhado)
        # como fonte da verdade de qual é o mais recente.
        exports = listar_exports(sessao, pasta_base)
        if not exports:
            return None
        export_id = exports[0]["id"]
    return carregar_export(sessao, export_id, pasta_base)


def listar_exports(sessao, pasta_base=PASTA_BASE_PADRAO):
    """Lista os exports desta sessão, do mais recente para o mais antigo."""
    if not _tem_identidade(sessao):
        return []

    pasta = _pasta_sessao(sessao, pasta_base)
    exports = _ler_metadata(pasta)
    return list(reversed(exports))


# ---------------------------------------------------------------------
# Elenco ("meu time"): diferente dos exports acima (vários, um upload de
# scouting por vez), o elenco é um único slot por sessão — o upload mais
# recente do "meu time" sempre substitui o anterior. Serve como base
# comparativa para a tela /elenco (ver app.py): em vez de comparar um
# export com outro no tempo (histórico antigo), compara-se um jogador
# escoutado com os jogadores que o usuário já tem.
# ---------------------------------------------------------------------

_NOME_ARQUIVO_ELENCO = "elenco.pkl"
_NOME_METADATA_ELENCO = "elenco_metadata.json"


def salvar_elenco(sessao, df, nome_arquivo, pasta_base=PASTA_BASE_PADRAO):
    """Salva/substitui o elenco ("meu time") desta sessão.

    Ao contrário de salvar_export(), não guarda histórico: um novo upload
    de elenco sempre substitui o anterior (o usuário só tem UM elenco
    atual, faz sentido comparar contra ele, não contra elencos antigos).

    Devolve os metadados salvos (nome do arquivo, data/hora, nº de
    jogadores).
    """
    pasta = _pasta_sessao(sessao, pasta_base)
    df.to_pickle(os.path.join(pasta, _NOME_ARQUIVO_ELENCO))

    metadata = {
        "nome_arquivo": nome_arquivo,
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "num_jogadores": int(len(df)),
    }
    with open(os.path.join(pasta, _NOME_METADATA_ELENCO), "w", encoding="utf-8") as arquivo:
        json.dump(metadata, arquivo, ensure_ascii=False, indent=2)

    return metadata


def carregar_elenco(sessao, pasta_base=PASTA_BASE_PADRAO):
    """Carrega o DataFrame do elenco desta sessão, ou None se ainda não
    houver um elenco enviado (ou se o cache tiver sido perdido)."""
    if not _tem_identidade(sessao):
        return None

    pasta = _pasta_sessao(sessao, pasta_base)
    caminho = os.path.join(pasta, _NOME_ARQUIVO_ELENCO)
    if not os.path.exists(caminho):
        return None

    try:
        return pd.read_pickle(caminho)
    except (OSError, ValueError, pickle.UnpicklingError):
        return None


def elenco_metadata(sessao, pasta_base=PASTA_BASE_PADRAO):
    """Metadados do elenco desta sessão (nome do arquivo, data/hora, nº de
    jogadores), ou None se ainda não houver elenco enviado."""
    if not _tem_identidade(sessao):
        return None

    pasta = _pasta_sessao(sessao, pasta_base)
    caminho = os.path.join(pasta, _NOME_METADATA_ELENCO)
    if not os.path.exists(caminho):
        return None

    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return None


def remover_elenco(sessao, pasta_base=PASTA_BASE_PADRAO):
    """Remove o elenco salvo desta sessão (ex: botão "Trocar elenco")."""
    if not _tem_identidade(sessao):
        return

    pasta = _pasta_sessao(sessao, pasta_base)
    for nome in (_NOME_ARQUIVO_ELENCO, _NOME_METADATA_ELENCO):
        caminho = os.path.join(pasta, nome)
        if os.path.exists(caminho):
            os.remove(caminho)
