import os
import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from src.data_generator import generate_synthetic_data
from src.data_ingestion import init_db, ingest_raw_data
from src.attribution_models import get_attribution_report

app = FastAPI(
    title="Marketing Traffic & Attribution Pipeline (MTA-API)",
    description="API para consultar métricas de atribuição multicanal e otimização de investimentos de marketing.",
    version="1.0.0"
)

# Montar a pasta de arquivos estáticos para o dashboard
app.mount("/dashboard", StaticFiles(directory="src/static", html=True), name="dashboard")

@app.get("/")
def read_root():
    return {
        "project": "Marketing Traffic & Attribution Pipeline (MTA-Pipeline)",
        "status": "online",
        "available_endpoints": {
            "/ingest": "Gera dados sintéticos diários e carrega no Supabase",
            "/attribution?model=[markov|last_touch|first_touch|linear]": "Obtém as métricas de performance por canal baseadas no modelo",
            "/optimize?model=[markov|last_touch|first_touch|linear]": "Gera recomendações analíticas de realocação de orçamento"
        }
    }

@app.get("/ingest")
def trigger_ingestion():
    """
    Gatilhador de ingestão: gera novos dados sintéticos e reconstrói as tabelas no Supabase.
    Simula um pipeline diário sob demanda.
    """
    try:
        # 1. Gerar novos arquivos locais
        generate_synthetic_data(days=30, num_users=5000)
        
        # 2. Inicializar tabelas e ingerir
        init_db()
        ingest_raw_data()
        
        return {
            "status": "success",
            "message": "Novos dados gerados e inseridos com sucesso no Supabase!"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro durante a ingestão do pipeline: {str(e)}"
        )

@app.get("/attribution")
def get_attribution(
    model: str = Query(
        "markov", 
        description="Modelo de atribuição: 'markov', 'last_touch', 'first_touch' ou 'linear'"
    )
):
    """
    Retorna o relatório financeiro de marketing consolidado para o modelo selecionado.
    """
    allowed_models = ["markov", "last_touch", "first_touch", "linear"]
    if model not in allowed_models:
        raise HTTPException(
            status_code=400,
            detail=f"Modelo inválido. Escolha um entre: {allowed_models}"
        )
        
    try:
        df_report = get_attribution_report()
        
        if df_report.empty:
            return {
                "message": "Nenhum dado encontrado no banco. Execute /ingest primeiro para popular as tabelas."
            }
            
        # Selecionar e formatar as colunas de interesse com base no modelo
        cols_to_keep = [
            'channel', 'impressions', 'clicks', 'spend',
            f'{model}_rev', f'{model}_conv', f'{model}_roas', f'{model}_cac'
        ]
        
        df_filtered = df_report[cols_to_keep].copy()
        
        # Renomear colunas para simplificar a resposta da API
        df_filtered.rename(columns={
            f'{model}_rev': 'revenue_attributed',
            f'{model}_conv': 'conversions_attributed',
            f'{model}_roas': 'roas',
            f'{model}_cac': 'cac'
        }, inplace=True)
        
        # Converter para lista de dicionários para resposta JSON
        data = df_filtered.to_dict(orient='records')
        
        # Adicionar consolidados globais na resposta
        total_spend = df_report['spend'].sum()
        total_revenue = df_report[f'{model}_rev'].sum()
        overall_roas = round(total_revenue / total_spend, 2) if total_spend > 0 else 0.0
        
        return {
            "model_applied": model,
            "overall_summary": {
                "total_spend": round(total_spend, 2),
                "total_revenue_attributed": round(total_revenue, 2),
                "overall_roas": overall_roas
            },
            "data": data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao calcular relatório de atribuição: {str(e)}"
        )

@app.get("/optimize")
def get_optimization(
    model: str = Query(
        "markov", 
        description="Modelo de atribuição de referência para otimização"
    )
):
    """
    Retorna recomendações analíticas de otimização de orçamento baseadas no ROAS de cada canal.
    Canais pagos com ROAS acima da média ganham sugestão de incremento de verba.
    Canais com ROAS abaixo da média ganham recomendação de redução.
    """
    try:
        df_report = get_attribution_report()
        
        if df_report.empty:
            raise HTTPException(
                status_code=400,
                detail="Nenhum dado disponível. Execute /ingest primeiro."
            )
            
        roas_col = f'{model}_roas'
        
        # Filtrar apenas canais que possuem investimento (custo > 0)
        df_paid = df_report[df_report['spend'] > 0].copy()
        
        if df_paid.empty:
            return {"message": "Sem canais pagos registrados com investimentos ativos."}
            
        mean_roas = df_paid[roas_col].mean()
        
        recommendations = []
        for _, row in df_paid.iterrows():
            ch = row['channel']
            ch_roas = row[roas_col]
            ch_spend = row['spend']
            
            # Comparação simples de ROAS contra a média dos canais pagos
            if ch_roas > mean_roas * 1.2:
                status = "Excelente Performance"
                action = "Aumentar Orçamento"
                sug_pct = 20.0
                reason = f"O ROAS do canal ({ch_roas}) está 20% ou mais acima da média de canais pagos ({round(mean_roas, 2)})."
            elif ch_roas < mean_roas * 0.8:
                status = "Baixa Performance"
                action = "Reduzir Orçamento"
                sug_pct = -15.0
                reason = f"O ROAS do canal ({ch_roas}) está 20% ou mais abaixo da média de canais pagos ({round(mean_roas, 2)})."
            else:
                status = "Performance Estável"
                action = "Manter Orçamento"
                sug_pct = 0.0
                reason = f"O ROAS do canal ({ch_roas}) está dentro da média esperada do mix de mídia ({round(mean_roas, 2)})."
                
            recommendations.append({
                "channel": ch,
                "current_spend": round(ch_spend, 2),
                "roas": round(ch_roas, 2),
                "channel_status": status,
                "recommended_action": action,
                "suggested_budget_change_pct": sug_pct,
                "rationale": reason
            })
            
        return {
            "model_reference": model,
            "average_paid_roas": round(mean_roas, 2),
            "recommendations": recommendations
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao computar recomendações: {str(e)}"
        )

if __name__ == '__main__':
    # Obter porta do ambiente ou usar 8000 por padrão
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("src.api:app", host=host, port=port, reload=True)
