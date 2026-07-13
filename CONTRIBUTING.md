# Contribuindo com o FM Scouting

Obrigado pelo interesse! Este é um projeto pessoal, então o fluxo é
simples — mas o básico de sempre ajuda a manter tudo funcionando.

## Rodando o projeto localmente

```bash
git clone <url-do-repo>
cd fm-scouting
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse http://localhost:5000. Veja o `README.md` para detalhes sobre a
variável `FLASK_SECRET_KEY` e a seção de deploy em produção.

## Rodando os testes

```bash
pip install -r requirements-dev.txt
pytest
```

A suíte cobre `scouting/parser.py`, `scouting/formulas/`,
`scouting/ranking.py`, `scouting/sessao.py` e um conjunto de testes de
integração leves que sobem o app Flask de verdade (`tests/test_app.py`).

**Antes de abrir um PR, rode `pytest` e confirme que tudo passa.** Se
você adicionar uma métrica nova, uma rota nova, ou mudar o comportamento
de alguma existente, adicione (ou ajuste) o teste correspondente na
mesma mudança — não em um PR separado depois.

O CI (`.github/workflows/tests.yml`) roda a suíte automaticamente em
todo push/PR para a `main`, então qualquer quebra aparece ali mesmo sem
rodar localmente antes — mas rodar localmente primeiro é bem mais rápido
que esperar o CI.

## Estrutura do projeto

Veja a seção "Estrutura" do `README.md` para um mapa de onde cada coisa
mora (`app.py`, `scouting/`, `templates/`, `static/`).

## Estilo de commit

Sem convenção rígida (tipo Conventional Commits), mas siga o padrão já
usado no histórico do repo:

- Mensagem no imperativo, em português, descrevendo o que a mudança faz
  (ex: `Corrige isolamento de rate limit entre testes`, não
  `Corrigido` ou `Fix`).
- Prefira commits pequenos e focados em uma coisa só a um commit gigante
  misturando funcionalidades diferentes — facilita revisar e reverter se
  precisar.
- Se a mudança mexe em `scouting/formulas/` ou em qualquer cálculo de
  métrica, mencione no commit qual métrica/fórmula mudou e por quê (o
  "porquê" importa mais que o "o quê" aqui, já que o diff já mostra o
  "o quê").

## Adicionando uma métrica/coluna nova

Se for adicionar uma métrica calculada nova (ex: uma fórmula nova de
`scouting/formulas/volantes.py`):

1. Calcule a coluna nova em `scouting/formulas/volantes.py`.
2. Adicione o nome dela em `scouting/colunas/volantes.py`, na aba
   (categoria) onde ela deve aparecer.
3. Se a coluna for percentual, monetária ou precisar de formatação
   especial, confira `formatar_valor()` em `app.py`.
4. Adicione um teste em `tests/test_volantes_formulas.py` cobrindo o
   cálculo (valores esperados a partir de um export de exemplo).

## Roadmap

O `ROADMAP.md` lista os itens já feitos e os pendentes, organizados por
fase (segurança, performance, produto, maturidade do repo,
acessibilidade). Se você quiser atacar algum item de lá, sinta-se à
vontade — só vale checar se não tem alguma decisão em aberto anotada
junto do item (alguns dependem de uma escolha de produto antes de
implementar).
