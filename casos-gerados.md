# Casos de teste de integração gerados pela LLM

As tabelas registram as saídas da experiência descrita em [prompts.md](prompts.md). Os IDs correspondem aos nomes dos testes em [tests/test_integration.py](tests/test_integration.py).

## Saída de P1

Precondição de cada caso: dois serviços ativos e estoque de `LIVRO-001` igual a 5. As chamadas são feitas a `POST /orders`.

| ID | Cenário | Entrada JSON | Resultado esperado |
| --- | --- | --- | --- |
| CT01 | Pedido válido | `{"sku":"LIVRO-001","quantity":2}` | HTTP 201; pedido confirmado; estoque final 3. |
| CT02 | Estoque insuficiente | `{"sku":"LIVRO-001","quantity":6}` | HTTP 409, `insufficient_stock`; estoque permanece 5. |
| CT03 | SKU inexistente | `{"sku":"INEXISTENTE","quantity":1}` | Estoque retorna 404, pedidos converte em HTTP 422, `unknown_sku`; estoque existente permanece 5 e SKU inexistente não é criado. |
| CT04 | Quantidade zero | `{"sku":"LIVRO-001","quantity":0}` | HTTP 400, `invalid_payload`; estoque permanece 5. |
| CT05 | Quantidade negativa | `{"sku":"LIVRO-001","quantity":-1}` | HTTP 400, `invalid_payload`; estoque permanece 5. |
| CT06 | Quantidade textual | `{"sku":"LIVRO-001","quantity":"2"}` | HTTP 400, `invalid_payload`; estoque permanece 5. |
| CT07 | Campo obrigatório ausente | `{"sku":"LIVRO-001"}` | HTTP 400, `invalid_payload`; estoque permanece 5. |

CT01 também verifica, conforme o contrato do P2 refinado: `order_id` válido como UUID, `status` igual a `confirmed`, `sku` correspondente, `quantity` inteira igual a 2, conjunto exato de campos e conteúdo JSON.

## Saída de P2 refinado

Cada caso inicia com um banco novo, cinco unidades e ambos os serviços ativos. As exceções e ações específicas estão na tabela.

| ID | Cenário | Entrada ou ação | Resultado esperado |
| --- | --- | --- | --- |
| CT08 | Quantidade booleana | `POST /orders` com `{"sku":"LIVRO-001","quantity":true}` | HTTP 400, `invalid_payload`; estoque permanece 5. |
| CT09 | Limite exato e esgotamento | Pedido de 5 unidades; depois pedido de 1 unidade | Primeiro HTTP 201 e estoque 0; segundo HTTP 409, `insufficient_stock`; estoque continua 0. |
| CT10 | JSON malformado | Enviar os bytes de `{"sku":` para `/orders` | HTTP 400, `invalid_json`; estoque permanece 5. |
| CT11 | Estoque indisponível | Encerrar o servidor de estoque; enviar pedido de 1 unidade | HTTP 503, `inventory_unavailable`; banco preservado com 5 unidades. |
| CT12 | Concorrência pela última disponibilidade | Enviar dois pedidos de 4 unidades com dois clientes concorrentes | Exatamente um HTTP 201 e um HTTP 409 com `insufficient_stock`, independentemente da ordem; estoque final 1. |
| CT13 | SKU em branco | `POST /orders` com `{"sku":"   ","quantity":1}` | HTTP 400, `invalid_payload`; estoque permanece 5. |
| CT14 | JSON de tipo incorreto | `POST /orders` com `["LIVRO-001",1]` | HTTP 400, `invalid_payload`; estoque permanece 5. |
| CT15 | Contrato de reserva | `POST /reservations` diretamente no estoque com `{"sku":"LIVRO-001","quantity":1}` | HTTP 200, corpo exatamente `{"sku":"LIVRO-001","quantity":1,"remaining":4}`, Content-Type JSON e estoque final 4. |

CT15 cobre a integração HTTP da API de estoque com SQLite. CT01, CT02, CT03, CT09 e CT12 exercitam o fluxo entre as duas APIs e o banco. CT11 verifica a falha de comunicação. Os demais casos verificam rejeições na fronteira HTTP de pedidos e a preservação do estoque.

## Verificação automatizada

```sh
python -m unittest discover -s tests -v
```

As verificações consultam o SQLite após as chamadas HTTP. A suíte não depende apenas da mensagem de resposta para confirmar a alteração ou preservação do estoque. CT12 cobre uma disputa com dois clientes; não representa um teste de carga ou uma prova para todos os possíveis escalonamentos concorrentes.
