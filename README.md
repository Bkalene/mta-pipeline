# Marketing Traffic & Attribution Pipeline (MTA-Pipeline)

Pipeline end-to-end de **Atribuição Multicanal (Multi-Touch Attribution)** com dashboard analítico interativo. Resolve um dos problemas mais críticos do marketing moderno: determinar o real impacto de cada canal de mídia sobre as conversões — eliminando o viés do modelo Last Touch e aplicando **Cadeias de Markov** para atribuição probabilística.

---

## Visão Geral da Solução

```mermaid
flowchart TD
    A[data_generator.py] -->|Gera CSVs locais| B[(Pasta /data)]
    B --> C[data_ingestion.py]
    D[.env Configs] --> C
    C -->|Cria Tabelas & Ingesta| E[(Supabase PostgreSQL)]
    E --> F[attribution_models.py]
    F -->|Markov · Last · First · Linear| G[api.py - FastAPI]
    G -->|/attribution · /optimize| H[Dashboard Interativo]
    H -->|Visualizações & KPIs| I[Tomador de Decisão]
```

---

## O Problema de Negócio

A jornada de compra raramente é linear. Um cliente pode:

1. Ver um anúncio no **TikTok Ads** e clicar — primeiro contato
2. Dias depois, pesquisar e acessar via **Google Ads** — consideração
3. Receber um e-mail de remarketing — reengajamento
4. Finalizar a compra via **Organic** — conversão

Com o modelo clássico **Last Touch**, 100% da receita seria atribuída ao canal *Organic* — levando à decisão errônea de cortar TikTok Ads e Google Ads, derrubando a receita futura.

**Este projeto resolve isso ao:**
- Rastrear a jornada completa de cliques por usuário (`cookie_id`)
- Computar **4 modelos de atribuição** em paralelo
- Aplicar **Cadeia de Markov Absorvente** com Efeito de Remoção (*Removal Effect*) para atribuição livre de viés
- Expor métricas de **ROAS**, **CAC** e **recomendações automáticas de orçamento** via API REST

---

## Dashboard Analítico

Acesse em: `http://localhost:8000/dashboard/`

### Funcionalidades do Dashboard

| Feature | Descrição |
|---|---|
| **4 KPIs Globais** | Investimento, Receita Atribuída, ROAS Geral e Conversões Totais com contador animado |
| **Gráfico de Barras** | Receita Atribuída vs. Investimento por canal para o modelo selecionado |
| **Gráfico de Rosca** | Mix de distribuição percentual de receita entre canais |
| **Comparação de Modelos** | ROAS de todos os 4 modelos lado a lado para cada canal |
| **Tabela do Otimizador** | Recomendações heurísticas de aumento/redução de verba com justificativa analítica |
| **Seletor de Modelo** | Troca em tempo real entre Markov, Last Touch, First Touch e Linear |
| **Ingestão On-Demand** | Botão para regerar dados sintéticos e repopular o Supabase sem sair do dashboard |
| **Toast Notifications** | Feedback visual de sucesso/erro sem `alert()` bloqueante |
| **Status do Pipeline** | Indicador na sidebar do estado da conexão em tempo real |

---

## Arquitetura dos Módulos

| Módulo | Responsabilidade |
|---|---|
| `src/data_generator.py` | Simula jornadas de usuário (cliques, conversões, gastos por canal) por 30 dias |
| `src/database.py` | Engine SQLAlchemy + gerenciamento de sessões com reconexão automática |
| `src/data_ingestion.py` | Criação das tabelas (`clicks`, `sales`, `ads_costs`) e bulk insert no Supabase |
| `src/attribution_models.py` | Modelos de atribuição: First Touch, Last Touch, Linear e Cadeia de Markov |
| `src/api.py` | FastAPI com endpoints `/ingest`, `/attribution`, `/optimize` e serve o dashboard estático |
| `src/static/` | Dashboard web: `index.html`, `styles.css`, `app.js` |

---

## Stack de Tecnologias

**Backend**
- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy + psycopg2-binary
- pandas, numpy
- python-dotenv

**Banco de Dados**
- PostgreSQL via **Supabase** (cloud)

**Frontend (Dashboard)**
- HTML5 semântico + Vanilla CSS + JavaScript (ES2022)
- Chart.js (gráficos de barras, rosca e comparação)
- Boxicons + Google Fonts (Outfit)
- Tema escuro com glassmorphism e micro-animações

**Matemática do Modelo Markov**

$$B = F \times R \quad \text{onde} \quad F = (I - Q)^{-1}$$

$F$ é a Matriz Fundamental que descreve o número esperado de transições nos estados temporários antes da absorção (conversão ou não-conversão). O *Removal Effect* de cada canal mede quanto a probabilidade de conversão cai ao remover aquele canal do mix.

---

## Setup e Execução

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/Bkalene/mta-pipeline.git
cd mta-pipeline

python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar o banco de dados Supabase

1. Crie um projeto gratuito em [supabase.com](https://supabase.com)
2. Vá em **Project Settings → Database → Connection String → URI**
3. Copie a string de conexão direta (porta 5432)
4. Crie o arquivo `.env` na raiz do projeto:

```env
SUPABASE_DB_URL=postgresql://postgres.SEU-PROJETO:SUA-SENHA@aws-0-sa-east-1.pooler.supabase.com:5432/postgres
PORT=8000
HOST=0.0.0.0
```

### 3. Popular o banco de dados

```bash
# Gerar CSVs sintéticos localmente
python src/data_generator.py

# Criar tabelas e ingerir dados no Supabase
python src/data_ingestion.py
```

### 4. Iniciar o servidor

```bash
python -m src.api
```

| URL | Descrição |
|---|---|
| `http://localhost:8000/dashboard/` | Dashboard analítico interativo |
| `http://localhost:8000/docs` | Swagger UI — documentação interativa da API |
| `http://localhost:8000/` | Status JSON da API |

---

## Endpoints da API

### `GET /ingest`
Gera novos dados sintéticos (30 dias / 5.000 usuários) e reconstrói as tabelas no Supabase. Simula um pipeline diário on-demand.

```json
{ "status": "success", "message": "Novos dados gerados e inseridos com sucesso no Supabase!" }
```

### `GET /attribution?model={modelo}`
Retorna o relatório financeiro consolidado por canal para o modelo escolhido.

**Parâmetros:** `model` → `markov` | `last_touch` | `first_touch` | `linear`

```json
{
  "model_applied": "markov",
  "overall_summary": {
    "total_spend": 8668.61,
    "total_revenue_attributed": 103257.10,
    "overall_roas": 11.91
  },
  "data": [
    {
      "channel": "TikTok Ads",
      "spend": 1329.29,
      "revenue_attributed": 23881.70,
      "conversions_attributed": 89.51,
      "roas": 17.97,
      "cac": 14.85
    }
  ]
}
```

### `GET /optimize?model={modelo}`
Analisa o ROAS de cada canal pago vs. a média do mix e gera recomendações automáticas de realocação de orçamento.

```json
{
  "model_reference": "markov",
  "average_paid_roas": 12.05,
  "recommendations": [
    {
      "channel": "TikTok Ads",
      "roas": 17.97,
      "channel_status": "Excelente Performance",
      "recommended_action": "Aumentar Orçamento",
      "suggested_budget_change_pct": 20.0,
      "rationale": "ROAS 20% acima da média do mix pago (12.05)."
    }
  ]
}
```

---

## Principais Insights Gerados

**1. Viés do Last Touch vs. Markov**
O modelo *Last Touch* tende a supervalorizar canais de retargeting (Email, Organic) que aparecem no final da jornada. O modelo de Markov redistribui o crédito proporcionalmente ao *Removal Effect* — canais que abrem novas jornadas (TikTok Ads, Google Ads) recebem crédito real pelo impacto incremental.

**2. Recomendação Dinâmica de Budget**
O endpoint `/optimize` calcula a média de ROAS dos canais pagos. Canais com ROAS ≥ 120% da média recebem sugestão de incremento de +20%. Canais com ROAS ≤ 80% da média recebem recomendação de redução de -15%, otimizando o CAC médio do portfólio.

**3. Comparação Visual entre Modelos**
O dashboard exibe o gráfico de comparação de ROAS entre todos os modelos simultaneamente, tornando visível como cada metodologia de atribuição altera a percepção de desempenho de cada canal — informação crítica para escolha do modelo de medição.

---

## Licença

MIT — sinta-se livre para adaptar e utilizar.
