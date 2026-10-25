# Registro dos prompts

## Identificação da experiência

- Data: 25/10/2026.
- LLM: assistente Codex nesta conversa.
- Método: geração nesta própria sessão, seguida de implementação e execução local com `unittest`. Não foi utilizado um segundo provedor nem uma chamada externa a uma API de LLM.
- Saídas: casos em [casos-gerados.md](casos-gerados.md) e implementação em [tests/test_integration.py](tests/test_integration.py).
- Escopo: cenário didático definido para esta atividade. Os resultados não correspondem à execução de um sistema de produção.

## P1 — Prompt direto, sem exemplos (zero-shot)

```text
Gere casos de teste de integração para uma API de pedidos que chama uma
API de estoque por HTTP. O estoque inicial é de 5 unidades de LIVRO-001.
O cliente envia POST /orders com sku e quantity; a API de pedidos chama
POST /reservations. A quantidade deve ser um inteiro positivo.
Pedidos aceitos retornam 201 e reduzem o estoque; quantidade ou campos
inválidos retornam 400; estoque insuficiente retorna 409; SKU inexistente
retorna 422 ao cliente. Gere sete casos com entrada e resultado esperado.
```

Saída registrada: CT01 a CT07, na primeira tabela do arquivo de casos. Essa rodada forneceu a base inicial da suíte.

## P2 — Prompt com papel, restrições e contrato de saída

```text
Atue como engenheiro de qualidade responsável pela integração entre as
APIs de pedidos e estoque descritas no P1. Revise os sete casos já gerados
e proponha casos adicionais de borda, falha de comunicação e contrato.
Considere também duas solicitações concorrentes e não repita os casos
iniciais. Para cada caso, informe entrada e resultado esperado.
```

Saída preliminar desta rodada:

1. Rejeitar quantidade booleana.
2. Reservar a quantidade exata disponível e tentar novo pedido.
3. Enviar JSON malformado.
4. Interromper o serviço de estoque.
5. Disputar estoque com dois pedidos simultâneos.
6. Enviar SKU em branco.
7. Enviar JSON que não seja um objeto.
8. Verificar a resposta da reserva de estoque.

## P2 refinado — Restrições verificáveis e estado do banco

```text
Transforme as oito sugestões do P2 em casos executáveis e determinísticos.
Use Python unittest, servidores HTTP locais reais e SQLite; não use mocks
na comunicação entre pedidos e estoque. Cada teste deve começar com
5 unidades de LIVRO-001, usar portas dinâmicas e encerrar seus servidores.

Contrato adicional:
- bool não é uma quantidade válida, mesmo que Python o trate como int;
- SKU em branco e JSON que não seja objeto retornam 400 invalid_payload;
- JSON malformado retorna 400 invalid_json;
- conexão recusada com o estoque retorna 503 inventory_unavailable;
- reserva direta aceita retorna 200 com sku, quantity e remaining;
- pedido aceito retorna 201 com order_id UUID, status confirmed, sku e quantity;
- reserva de SKU inexistente retorna 404 no estoque, convertido em 422 em pedidos;
- estoque insuficiente retorna 409 insufficient_stock;
- todas as respostas têm Content-Type application/json.

Para indisponibilidade, encerre o servidor de estoque antes da chamada.
Para concorrência, envie dois pedidos de 4 unidades e aceite qualquer ordem
de conclusão, mas exija exatamente um 201, um 409 e estoque final igual a 1.
Verifique status, corpo e estoque persistido, inclusive a ausência de alterações
em falhas. Não invente autenticação, pagamentos, retentativas ou idempotência.
Retorne os oito casos com ID, precondição, entrada/ação e resultado esperado.
```

Saída registrada: CT08 a CT15, na segunda tabela do arquivo de casos. O contrato de sucesso também foi incorporado às asserções de CT01.
