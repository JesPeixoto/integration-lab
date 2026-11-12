# Como o Integration Lab funciona

Este documento explica o projeto em português, para consulta e estudo. O código
e os nomes de API ficam em inglês; a documentação fica no idioma de quem mantém
o projeto.

## O problema

Sistemas modernos falam JSON e REST. Sistemas legados costumam falar XML e
protocolos próprios. Alguém precisa fazer a tradução, tratar falhas e garantir
que uma requisição repetida não crie duplicidade.

## O fluxo de uma requisição

1. O cliente chama `POST /api/v1/suppliers` com JSON e o header `X-API-Key`.
2. A API valida o payload com Pydantic.
3. Se veio `Idempotency-Key`, o serviço verifica se aquela chave já foi usada.
4. O adapter converte o JSON em XML.
5. O cliente HTTP chama o ERP simulado.
6. Se o ERP falhar com timeout, `429` ou `5xx`, o cliente tenta de novo com
   backoff exponencial e jitter.
7. A resposta XML é convertida para JSON e o status fica registrado.

## Por que idempotência

Se o cliente enviar a mesma requisição duas vezes (porque a primeira demorou ou
a resposta se perdeu), a segunda não deve criar outro fornecedor.

A chave `Idempotency-Key` resolve isso no lado da API:

- mesma chave e mesmo payload: devolve o resultado original;
- mesma chave e payload diferente: `409`, porque a chave está sendo reutilizada
  para outra intenção;
- falha transitória: a chave é liberada, permitindo nova tentativa.

Limitação importante: se o ERP criar o registro e a resposta se perder, a API
não tem como saber. Em produção, a chave também deveria ser enviada ao ERP ou
haver uma consulta de duplicidade no destino.

## Por que retry

Nem toda falha é definitiva. Timeout, `429` e `5xx` podem ser temporários. Já um
`422` de regra de negócio não melhora se repetirmos a chamada.

O retry usa backoff exponencial com jitter para não martelar o ERP:

- tentativa 1: espera base;
- tentativa 2: dobra a espera;
- tentativa 3: dobra de novo, até o limite configurado.

## Por que API key

A API e o ERP exigem `X-API-Key`. Isso demonstra autenticação entre serviços.
Em produção, o ideal é combinar com HTTPS, rotação de chaves e um cofre de
segredos.

## Como os testes cobrem

- `tests/test_suppliers.py`: fluxo da API, autenticação, validação, erro do ERP,
  idempotência e liberação da chave em falha.
- `tests/test_erp_client.py`: montagem do XML, parsing da resposta, retry e
  decisão de não repetir `4xx`.
- `tests/test_mock_erp.py`: contrato do ERP simulado.

## O que eu faria em produção

- Persistir integrações e chaves de idempotência em banco.
- Propagar a chave de idempotência para o ERP ou consultar duplicidade antes de
  inserir.
- Adicionar métricas (latência, taxa de erro, tentativas) e tracing.
- Usar fila ou outbox para desacoplar a chamada do ERP do request HTTP.
- Configurar circuit breaker para não insistir em um ERP indisponível.
- Rodar com HTTPS e segredos em cofre.

## Perguntas para estudar antes de uma entrevista

1. O que acontece se o ERP criar o fornecedor e a resposta se perder?
2. Por que não faz sentido repetir um erro `422`?
3. Por que separar o contrato JSON do contrato XML?
4. Qual é a diferença entre idempotência no cliente e no servidor?
5. O que mudaria se o volume de requisições crescesse 100 vezes?
6. Onde os logs ajudariam a investigar uma falha de integração?
