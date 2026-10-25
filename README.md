# Testes de integração de APIs com apoio de GenAI

Atividade da Unidade III: geração de casos de integração por dois tipos de prompt e execução automatizada dos casos.

## Cenário

Um cliente envia `POST /orders` à API de pedidos. Ela chama `POST /reservations` na API de estoque por HTTP. O estoque consulta e atualiza um banco SQLite. Cada teste inicia os dois servidores em portas locais atribuídas pelo sistema e recebe um banco novo com cinco unidades de `LIVRO-001`.

```text
Cliente de teste -> API de pedidos -> HTTP -> API de estoque -> SQLite
```

Os servidores HTTP, a comunicação de rede e o SQLite são reais; não há mocks das chamadas entre serviços. Os cenários de entrada inválida verificam a fronteira HTTP da API de pedidos e a preservação do banco, sem precisar alcançar o serviço de estoque.

## Execução

Requisito: Python 3.10 ou superior. O projeto usa somente a biblioteca padrão e não exige instalar pacotes, obter chaves de API ou acessar serviços externos.

Na raiz do projeto:

```sh
python -m unittest discover -s tests -v
```

Resultado esperado: 15 testes aprovados. Os servidores são iniciados e encerrados pelos próprios testes.

## Contratos usados no exercício

As duas APIs recebem um objeto JSON com `sku` (texto não vazio) e `quantity` (inteiro maior que zero; booleanos não são aceitos).

| API | Condição | HTTP | Corpo |
| --- | --- | --- | --- |
| Estoque | Reserva aceita | 200 | `sku`, `quantity`, `remaining` |
| Estoque | SKU inexistente | 404 | `{"error":"unknown_sku"}` |
| Estoque | Estoque insuficiente | 409 | `{"error":"insufficient_stock"}` |
| Pedidos | Pedido aceito | 201 | `order_id` (UUID), `status` (`confirmed`), `sku`, `quantity` |
| Pedidos | SKU inexistente no estoque | 422 | `{"error":"unknown_sku"}` |
| Pedidos | Estoque insuficiente | 409 | `{"error":"insufficient_stock"}` |
| Pedidos | Estoque indisponível | 503 | `{"error":"inventory_unavailable"}` |
| Ambas | JSON malformado | 400 | `{"error":"invalid_json"}` |
| Ambas | Campos inválidos | 400 | `{"error":"invalid_payload"}` |

As respostas são JSON. Uma rejeição não deve alterar o estoque. Duas reservas concorrentes não podem vender mais unidades do que as disponíveis. Esses contratos são decisões deste exercício, não regras universais para APIs REST.

## Arquivos

- [app.py](app.py): APIs de pedidos e estoque, persistência e inicialização dos servidores.
- [tests/test_integration.py](tests/test_integration.py): testes executáveis, identificados de CT01 a CT15.
- [prompts.md](prompts.md): prompts utilizados na sessão de LLM e identificação da experiência.
- [casos-gerados.md](casos-gerados.md): respostas estruturadas em casos de teste e rastreabilidade com os prompts.

## Limites do exemplo

O SQLite é temporário e fica em memória durante cada teste. A API de pedidos não persiste pedidos; confirma a reserva e retorna um identificador. Não há autenticação, pagamento, retentativas, idempotência ou transação distribuída. A suíte cobre o contrato descrito e não demonstra prontidão para produção.

## Publicação no GitHub

Os arquivos foram preparados localmente. Após criar um repositório vazio no GitHub, execute na raiz, substituindo o endereço pelo seu:

```sh
git init
git add .
git commit -m "Adiciona experimento de prompts e testes de integração"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git push -u origin main
```

Use o endereço real desse repositório na postagem do fórum após a publicação.
