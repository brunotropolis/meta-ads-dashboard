# Meta Ads Dashboard

Dashboard de performance de anúncios Meta (Facebook/Instagram Ads) para as contas MRN (Manual do Recém-Nascido) e Dream Baby.

## Arquitetura

```
Meta Ads API (Graph API v21.0)
        ↓ Campaign Collector (hourly, 8h-22h BRT)
Google Sheets "META ADS | Dashboard v1"
        ↓ Dashboard API (webhook GET)
Dashboard HTML (GitHub Pages)
        ↑ Daily Refresh (hourly) → Claude Haiku → AI_Recomendacoes
        ↑ Webhook Greenn → aba Vendas
```

- **Collector** é o UNICO componente que chama a Meta Ads API
- **Dashboard API** lê SOMENTE do Google Sheets (nunca chama Meta API)
- **Frontend** consome o Dashboard API via fetch + AbortController
- **Greenn Webhook** recebe vendas em tempo real para calcular ROAS real

## URLs e Acessos

| Recurso | URL |
|---|---|
| Dashboard (prod) | https://brunotropolis.github.io/meta-ads-dashboard/ |
| Dashboard API | https://n8n-n8n.xktssy.easypanel.host/webhook/meta-dashboard-api |
| Greenn Webhook | https://n8n-n8n.xktssy.easypanel.host/webhook/meta-greenn-vendas |
| Google Sheets | https://docs.google.com/spreadsheets/d/1RmxLFxQuCQaMSiYrOKpsk7yDEy82jJWw88MrLQhf-7Q |
| Repo GitHub | https://github.com/brunotropolis/meta-ads-dashboard |

## Workflows n8n

| ID | Nome | Trigger | Função |
|---|---|---|---|
| `vrV6PalbJQFM0VKw` | META \| Campaign Collector | Schedule 1h (8h-22h BRT) | Coleta campanhas Meta API → aba Campanhas |
| `1mpyzhlC5Nt5LjH0` | META \| Dashboard API | Webhook GET | Lê sheets → JSON para frontend |
| `aSE4xPbBzR46IvTp` | META \| Daily Refresh | Schedule 1h (8h-22h BRT) | Coleta criativos + análise Claude → abas Criativos + AI_Recomendacoes |
| `gWFz6MCkY4p2mizi` | META \| Webhook Greenn | Webhook POST | Recebe vendas Greenn → aba Vendas |

Config salvo em: `D:\CLAUDE\v2-workflows\meta_config.json`

## Google Sheets — Estrutura

**ID:** `1RmxLFxQuCQaMSiYrOKpsk7yDEy82jJWw88MrLQhf-7Q`

| Aba | Colunas | Atualização |
|---|---|---|
| `Campanhas` | conta, campaign_id, campaign_name, spend, impressions, clicks, ctr, cpc, cpm, conversions, conversion_value, roas, data, hora, criado_em | Hourly (clear + rewrite) |
| `Criativos` | conta, ad_id, ad_name, adset_name, campaign_name, spend, impressions, clicks, ctr, cpc, conversions, conversion_value, thumbnail_url, data_inicio, data_fim, criado_em | Hourly (clear + rewrite) |
| `AI_Recomendacoes` | data, conta, campanha_id, campanha_nome, tipo, motivo, acao_sugerida, status | Hourly (append) |
| `Vendas` | data, produto, valor, cliente_nome, cliente_email, cliente_telefone, transaction_id, status, criado_em | Webhook (append) |
| `Produtos_Funil` | produto_id, offer_hash, nome, preco | Manual (config) |
| `controle` | chave, valor (last_sync, last_ai_run) | Automático |

### Padrão Clear + Rewrite
O Collector **limpa** a aba Campanhas (A2:O5000) e **reescreve** todos os dados a cada hora. Isso garante dados sempre frescos sem duplicação. Mesmo padrão para Criativos.

## Contas Meta monitoradas

| Variável | Account ID | Nome |
|---|---|---|
| `ACCOUNT_MRN` | `act_1039575534353657` | MANUAL DO RECÉM-NASCIDO |
| `ACCOUNT_DB` | `act_972170058214168` | DREAM BABY - DB |

Token Meta e IDs ficam em `D:\CLAUDE\.env.meta` (não commitado).

## Campaign Collector — Detalhes

**Script:** `D:\CLAUDE\v2-workflows\build_meta_campaign_collector.py`
**Workflow:** `vrV6PalbJQFM0VKw`

### Fluxo (7 nodes)
```
SCHEDULE → HORA BRT → IF HORARIO (8h-22h) → COLETAR CAMPANHAS → IF TEM DADOS → LIMPAR + SALVAR CAMPANHAS → ATUALIZAR CONTROLE
```

### Meta API calls
Faz DUAS chamadas por conta para cobrir dados completos:
1. `date_preset=last_30d` + `time_increment=1` → últimos 30 dias completos (exclui hoje)
2. `date_preset=today` → dados parciais do dia atual

Campos: `campaign_id, campaign_name, spend, impressions, clicks, ctr, cpc, cpm, actions, action_values`

Conversões extraídas de `actions` filtrando: `purchase`, `offsite_conversion.fb_pixel_purchase`, `omni_purchase`

### Por que duas chamadas?
`last_30d` retorna apenas dias **completos** (D-30 a D-1). Sem a chamada `today`, o investimento do dia atual aparece como R$0.

## Dashboard API — Detalhes

**Script:** `D:\CLAUDE\v2-workflows\build_meta_dashboard_api.py`
**Workflow:** `1mpyzhlC5Nt5LjH0`
**Endpoint:** `GET /webhook/meta-dashboard-api`

### Parâmetros
| Param | Valores | Default |
|---|---|---|
| `periodo` | `hoje`, `ontem`, `semana`, `mes`, `personalizado` | `hoje` |
| `data_inicio` | `YYYY-MM-DD` (só com periodo=personalizado) | — |
| `data_fim` | `YYYY-MM-DD` (só com periodo=personalizado) | — |

### DATA_INICIO_DASHBOARD
```javascript
const DATA_INICIO_DASHBOARD = '2026-04-08';
```
**Regra:** nenhum período retorna dados anteriores a 08/04/2026. Isso evita distorção de ROAS (investimento Meta histórico sem vendas Greenn correspondentes). Se `inicio < DATA_INICIO_DASHBOARD`, é clampado para `2026-04-08`.

### Resposta JSON
```json
{
  "periodo": "semana",
  "data_inicio": "2026-04-08",
  "data_fim": "2026-04-09",
  "resumo": {
    "gasto_total": 1234.56,
    "impressoes": 50000,
    "cliques": 800,
    "ctr_medio": 1.6,
    "cpc_medio": 1.54,
    "conversoes_meta": 5,
    "roas_meta": 2.1,
    "faturamento_greenn": 3500.00,
    "roas_real": 2.83,
    "ticket_medio": 700.00
  },
  "campanhas": [...],
  "gasto_por_dia": [...],
  "criativos_top": [...],
  "recomendacoes": [...],
  "vendas": [...],
  "last_sync": "2026-04-09 14:00:05"
}
```

### CORS
`Access-Control-Allow-Origin: *`

## Daily Refresh — Detalhes

**Script:** `D:\CLAUDE\v2-workflows\build_meta_daily_refresh.py`
**Workflow:** `aSE4xPbBzR46IvTp`

### Fluxo (8 nodes)
```
SCHEDULE → COLETAR CRIATIVOS → IF TEM CRIATIVOS → LIMPAR + SALVAR CRIATIVOS
  → LER CAMPANHAS → ANALISE CLAUDE → SALVAR RECOMENDACOES → ATUALIZAR CONTROLE
```

### Criativos
- Meta API: `level=ad` com `date_preset=last_7d`
- Campos: `ad_id, ad_name, adset_name, campaign_name, spend, impressions, clicks, ctr, cpc, actions, action_values`
- Inclui `thumbnail_url` quando disponível

### Análise Claude (Haiku)
- Modelo: `claude-haiku-4-5-20251001`
- API key: env var `ANTHROPIC_API_KEY` no EasyPanel (n8n)
- Analisa campanhas com gasto > R$50 nos últimos 7 dias
- Identifica: alto CPC (>R$3), baixo CTR (<1%), alto ROAS (>5x = candidato a escalar)
- Tipos de recomendação: `PAUSAR`, `ESCALAR`, `AUMENTAR_BUDGET`, `DIMINUIR_BUDGET`, `MONITORAR`
- Salva com `status=NOVA` na aba AI_Recomendacoes

## Webhook Greenn — Detalhes

**Script:** `D:\CLAUDE\v2-workflows\build_meta_greenn_webhook.py`
**Workflow:** `gWFz6MCkY4p2mizi`
**Endpoint:** `POST /webhook/meta-greenn-vendas`

### Fluxo (4 nodes)
```
WEBHOOK (onReceived) → PARSE VENDA → APPEND VENDAS → RESPOND OK
```

- Recebe eventos da Greenn (compras aprovadas)
- Extrai: produto, valor, cliente (nome, email, telefone), transaction_id
- Append na aba Vendas com timestamp
- `responseMode: onReceived` → responde 200 OK instantaneamente

### Configurar na Greenn
URL do webhook: `https://n8n-n8n.xktssy.easypanel.host/webhook/meta-greenn-vendas`
Evento: `purchase.approved`

## Frontend Dashboard — Detalhes

**Arquivo:** `D:\CLAUDE\meta-ads-dashboard\index.html`
**URL pública:** https://brunotropolis.github.io/meta-ads-dashboard/
**Domínio custom:** https://dash.manualdorecemnascido.com.br/

### Tabs ativas (3)
- **📊 Overview** — cards principais + Performance por Conta + Métricas por UTM + Campanhas Ativas
- **📋 Campanhas** — tabela completa das campanhas do período
- **💰 Vendas** — Greenn breakdown, reembolsos, classificação por canal, lista de vendas

**Tabs removidas em Mai/2026:** Criativos, Por Hora, Recomendações, Assistente — UI ficou muito poluída, mantemos só o essencial.

### Cards do Overview (5 + 1 condicional)
| Card | Cálculo |
|---|---|
| 💵 Faturamento Bruto | Soma de vendas tipo=VENDA no período |
| 💰 Receita Líquida | `bruto − reembolsos − investimento Meta` (o que sobra pra nós) |
| 📢 Investimento Meta | Soma de spend das campanhas no período + delta vs ontem |
| 📊 ROAS de Mídia | `bruto ÷ Meta` (retorno bruto sobre ads, ignora reembolsos) |
| 🎯 ROAS do Projeto | `(bruto − reembolsos) ÷ Meta` — ROAS líquido de reembolsos. Só fica abaixo do ROAS de Mídia quando há reembolsos no período |
| 🎯 Campanhas Ativas | Só aparece em Hoje/Semana — escondido no Mês para reduzir ruído |

### Seção "Métricas por UTM" (Overview, todos os períodos)
Grid 2×2 com gráficos horizontais para 4 dimensões: **Source · Campaign · Medium · Content**. Cada barra mostra `count × R$ valor`. Endpoint expõe `vendas.por_utm`, `vendas.por_utm_campaign`, `vendas.por_utm_medium`, `vendas.por_utm_content`.

### Cards da tab Vendas (6)
Faturamento Bruto · Receita Líquida · Investimento Meta · Vendas/Reembolsos · ROAS de Mídia · ROAS do Projeto.

### Cache duplo (front + back)
1. **localStorage (TTL 5 min)** — render instantâneo no revisitar. Header mostra "Cache · Atualizando..." até receber dados frescos
2. **n8n static data (TTL 60s)** — `$getWorkflowStaticData('global').cache[periodo|dataIni|dataFim]`. Header `X-Cache: HIT/MISS` para debug. CHECK CACHE → IF CACHE HIT → RESPONDER CACHE (cache miss continua para LER SHEETS)

Resultado: 1ª chamada ~2.2s, chamadas seguintes ~50-100ms (40× mais rápido).

### Outros
- **AbortController** — cancela fetch anterior ao trocar período (n8n processa sequencialmente)
- **Auto-refresh:** 10 minutos
- **Timeout:** 25 segundos por request

### Tech
- Zero dependências externas
- CSS dark theme com variáveis
- Responsivo
- Sem Chart.js (tabelas only)

### AbortController — Por que é necessário
n8n processa webhooks **sequencialmente**. Se o frontend dispara 2 requests simultâneos (ex: page load + click em "Semana"), o segundo fica na fila esperando o primeiro terminar. O AbortController cancela o request anterior antes de disparar o novo.

## Deploy

### Deploy do HTML (GitHub Pages)
```bash
# Via GitHub Contents API (PUT) — evita popup de credencial do git
# Token: <github-pat-em-D:/CLAUDE/.env.meta>
# 1. GET SHA atual do arquivo
# 2. PUT com content base64 + SHA
```

Não usar `git push` — triggers diálogo de seleção de conta GitHub no Windows.

### Deploy dos workflows n8n
```bash
cd /d/CLAUDE/v2-workflows
python build_meta_campaign_collector.py    # Collector
python build_meta_dashboard_api.py         # Dashboard API
python build_meta_daily_refresh.py         # Daily Refresh + AI
python build_meta_greenn_webhook.py        # Greenn Webhook
```

Cada script: busca workflow existente por nome → deactivate → PUT → reactivate.

### Setup inicial (já executado)
```bash
python setup_meta_sheets.py <SHEETS_ID>   # Cria abas + headers
```

## Credenciais

| Recurso | ID/Ref |
|---|---|
| Google Sheets OAuth2 (n8n) | `6VV3tATljXfg5uvi` |
| n8n API Key | (ver scripts) |
| Meta Token | (ver `.env.meta` ou scripts) |
| Claude API (ANTHROPIC_API_KEY) | env var no EasyPanel |
| GitHub Token (deploy) | `<github-pat-em-D:/CLAUDE/.env.meta>` |

## Bugs conhecidos e resolvidos

1. **Dashboard "Atualizando..." infinito** — Dois fetch simultâneos bloqueavam n8n. Fix: AbortController.
2. **Hoje mostrando R$0** — Collector usava só `last_30d` (exclui hoje). Fix: adicionada chamada `today`.
3. **ROAS distorcido (0.75x)** — 30 dias de investimento vs 2 dias de vendas. Fix: `DATA_INICIO_DASHBOARD = '2026-04-08'` (renomeado depois para `DATA_INICIO_CAMPANHAS` aplicado só nas campanhas).
4. **n8n travado (6 execuções)** — Webhooks enfileirados. Fix: deactivate/reactivate workflow.
5. **git push popup** — Windows pede seleção de conta. Fix: deploy via GitHub Contents API.

## Bugs corrigidos (sessão Mai/2026 — receita líquida + UTMs + perf)

6. **Collector limitado a 8h-22h** — restringia atualização noturna. Fix: removido o nó `IF HORARIO`, Schedule conecta direto em `COLETAR CAMPANHAS`. Workflow tem agora 5 nós (Schedule → Coletar → IF Tem Dados → Limpar+Salvar → Atualizar Controle).
7. **`DATA_INICIO_DASHBOARD` cortava vendas antigas** — clamp aplicado a vendas também. Fix: renomeado para `DATA_INICIO_CAMPANHAS`, aplicado SÓ na agregação de campanhas (vendas vão até onde a planilha tiver).
8. **Receita Líquida não descontava Meta** — usuário queria "o que sobra pra nós". Fix: `receitaFinal = bruto − reembolsos − gastoMeta`. Cards "Resultado" e "Lucro Líquido" removidos por serem duplicatas.
9. **ROAS único confuso** — Fix: dois ROAS separados — **ROAS de Mídia** = `bruto ÷ Meta` · **ROAS do Projeto** = `(bruto − reembolsos) ÷ Meta`. (Inicialmente tinha subtraído Meta duas vezes no projeto — virou ROI em vez de ROAS, corrigido depois.)
10. **Dashboard travado "Carregando..."** — `renderChatChips()` órfão (chamada na init mesmo após remover tab Assistente) lançava TypeError quebrando `loadData()`. Fix: remover todo o bloco de chat (renderChatChips, sendChatMessage, handleChatKey etc.).
11. **`fatHoje is not defined`** — após renomear `fatHoje` → `fatLiquido`/`fatBruto`, ficou uma referência órfã em `deltaFat` de `renderOverview`. Fix: substituir por `fatLiquido`.
12. **Webhook Greenn não capturava UTMs (TODAS as vendas com source vazio)** — DOIS bugs no parser:
    - `sale.saleMetas || body.saleMetas` — `[]` é truthy em JS, sempre pegava o array vazio e nunca caía no fallback do root. Fix: `[...(sale.saleMetas || []), ...(body.saleMetas || [])]` mescla os dois.
    - UTMs lidas com `m.key || m.name` mas Greenn usa `m.meta_key`/`m.meta_value`. Fix: prefere `m.meta_key`, com fallback para outros providers.
13. **Backfill UTMs sobrescreveu data com `Date.now()`** — re-postar vendas pelo webhook fez `data` virar a data do backfill, não a da venda original. Fix: parser agora usa `sale.paid_at || sale.created_at` (`sale.refunded_at` para REEMBOLSO), com `new Date()` só como fallback.
14. **API lenta (~2-3s constante)** — gargalo era `batchGet` do Sheets puxando `Criativos` e `AI_Recomendacoes` (não usados mais). Fix: batchGet só pede `Campanhas + controle + Vendas`. Adicionado também **cache server-side no n8n** (TTL 60s via `$getWorkflowStaticData`) + cache localStorage no front (TTL 5min). Latência caiu de 2.2s → 50-100ms em cache hit.

## Integração Greenn API (descoberta Mai/2026)

Greenn está migrando para "Greenn Sales" mas o admin antigo (`adm.greenn.com.br`) ainda funciona. A API real fica em **`apiadm.greenn.com.br`** e responde com o JWT do cookie `access_token` (~1KB, começa com `Bearer eyJ0eXAiOiJKV1Qi...`).

| Endpoint | Descrição |
|---|---|
| `GET /api/sale?...` | Lista paginada de vendas. Resposta `{ data: { current_page, data: [...] } }` |
| `GET /api/sale/{id}` | Detalhe de uma venda + `metas[]` com utm_source/medium/campaign/content/src/ch_id etc |
| `GET /api/sale-total?...` | Totalizadores do período |

**Filtros importantes do `/api/sale`:**
- `status[]` (array Laravel — `[]` no nome, NÃO repetir o param)
- `method[]` (idem)
- `currency_id=1`, `date_start`, `date_end`, `page`, `per_page`, `type=created_at`, `signRenew=false`

Sem `status[]` no formato array dá 500. Sem `currency_id` dá 422.

### Script de backfill (referência)
Não foi salvo como arquivo porque depende do JWT do browser. Roda como JS no console de `adm.greenn.com.br`:
```js
const token = decodeURIComponent(document.cookie.split('; ').find(c=>c.startsWith('access_token='))?.split('=')[1] || '');
const dash = await (await fetch(`https://n8n-n8n.xktssy.easypanel.host/webhook/meta-dashboard-api?periodo=mes&_=${Date.now()}`)).json();
for (const v of (dash.vendas?.hoje || [])) {
  const sale = await (await fetch(`https://apiadm.greenn.com.br/api/sale/${v.transaction_id}`, { headers: { Authorization: token } })).json();
  await fetch('https://n8n-n8n.xktssy.easypanel.host/webhook/meta-greenn-vendas', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event: v.tipo === 'REEMBOLSO' ? 'saleRefunded' : 'saleUpdated',
      currentStatus: v.tipo === 'REEMBOLSO' ? 'refunded' : (sale.status || 'paid'),
      sale, saleMetas: sale.metas || [], customer: sale.client, product: sale.product, offer: sale.offer,
    }),
  });
  await new Promise(r => setTimeout(r, 400));
}
```
O webhook (`appendOrUpdate` matching por `transaction_id`) atualiza as linhas existentes — não cria duplicatas.

## Pendente

- **Painel de funil** — Após dados de produtos preenchidos, criar painel visual no dashboard.
- **Classificação de canal mais inteligente** — atualmente `[TRAFEGO]`, `[DRM]`, `[CBO]`, `RMKT` etc no `utm_source/campaign` caem em "Orgânico" porque o classificador só procura `facebook|google|meta`. Ajustar para reconhecer essas convenções como tráfego pago.
- **Vendas genuinamente sem UTM** — ~2 vendas/mês caem direto no Greenn sem nenhum tracking (cliente teclou URL direto). Não há o que backfill — esperado ficar como `(direto)`.

## Preview local

```
preview_start "meta-ads-dashboard"   →   http://localhost:XXXX
```
Configurar em `D:\CLAUDE\.claude\launch.json` se necessário.
