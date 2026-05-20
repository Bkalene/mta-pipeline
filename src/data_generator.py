import os
import random
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def generate_synthetic_data(days=30, num_users=5000, seed=42):
    """
    Gera dados sintéticos realistas de marketing digital e e-commerce para demonstrar
    modelos de atribuição (baseados em regras e Cadeias de Markov).
    """
    random.seed(seed)
    np.random.seed(seed)
    
    start_date = datetime.now() - timedelta(days=days)
    channels = ['Google Ads', 'Meta Ads', 'TikTok Ads', 'Email', 'Organic']
    
    # 1. Definir parâmetros de comportamento dos canais
    # Canal: (Probabilidade de ser o primeiro clique, Probabilidade de cliques seguintes, Custo Médio por Clique)
    channel_behaviors = {
        'Google Ads': {'first_click_prob': 0.35, 'subsequent_prob': 0.25, 'avg_cpc': 1.20, 'ctr': 0.04},
        'Meta Ads':   {'first_click_prob': 0.25, 'subsequent_prob': 0.40, 'avg_cpc': 1.80, 'ctr': 0.02},
        'TikTok Ads': {'first_click_prob': 0.30, 'subsequent_prob': 0.15, 'avg_cpc': 0.70, 'ctr': 0.03},
        'Email':      {'first_click_prob': 0.05, 'subsequent_prob': 0.15, 'avg_cpc': 0.00, 'ctr': 0.08},
        'Organic':    {'first_click_prob': 0.05, 'subsequent_prob': 0.05, 'avg_cpc': 0.00, 'ctr': 0.00}
    }
    
    # Gerar usuários únicos
    user_ids = [str(uuid.uuid4()) for _ in range(num_users)]
    
    click_records = []
    sales_records = []
    
    # Gerador de custos diários de anúncios
    daily_ads_costs = []
    
    # Inicializar contadores diários de cliques e custos para agregar depois
    daily_metrics = {date.strftime('%Y-%m-%d'): {ch: {'clicks': 0, 'impressions': 0, 'spend': 0.0} for ch in channels} 
                     for date in (start_date + timedelta(n) for n in range(days))}
    
    # 2. Simular comportamento do usuário e jornada de compra
    for user_id in user_ids:
        # Define se o usuário vai converter (comprar) ou não nesta simulação
        # Cerca de 8% de taxa de conversão simulada de usuários que interagem
        will_convert = random.random() < 0.08
        
        # Determina o tamanho da jornada (quantidade de interações/cliques do usuário)
        # Usuários que convertem tendem a ter jornadas maiores do que quem não converte
        if will_convert:
            journey_length = random.randint(1, 4)
        else:
            journey_length = random.randint(1, 2)
            
        user_clicks = []
        user_start_time = start_date + timedelta(
            days=random.randint(0, days - 2),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Gerar os cliques do usuário ao longo do tempo
        current_time = user_start_time
        for i in range(journey_length):
            # No primeiro clique, usa probabilidades de entrada/descoberta
            if i == 0:
                probs = [channel_behaviors[ch]['first_click_prob'] for ch in channels]
            else:
                probs = [channel_behaviors[ch]['subsequent_prob'] for ch in channels]
                
            # Normalizar probabilidades
            probs = np.array(probs) / sum(probs)
            channel = np.random.choice(channels, p=probs)
            
            # Registrar o clique do usuário
            click_id = str(uuid.uuid4())
            click_records.append({
                'click_id': click_id,
                'cookie_id': user_id,
                'timestamp': current_time,
                'channel': channel
            })
            
            # Acumular custos e cliques no painel diário se for pago
            date_str = current_time.strftime('%Y-%m-%d')
            if date_str in daily_metrics:
                daily_metrics[date_str][channel]['clicks'] += 1
                
            # Incrementar tempo para o próximo clique (algumas horas a 1 dia depois)
            current_time += timedelta(
                hours=random.randint(1, 24),
                minutes=random.randint(0, 59)
            )
            
        # Se o usuário converteu, gera uma venda logo após o último clique
        if will_convert:
            sale_time = current_time + timedelta(minutes=random.randint(5, 120))
            sale_id = str(uuid.uuid4())
            # Valor da venda realista (Ticket Médio de E-commerce de R$ 80 a R$ 450)
            revenue = round(random.uniform(80.0, 450.0), 2)
            
            sales_records.append({
                'sale_id': sale_id,
                'cookie_id': user_id,
                'timestamp': sale_time,
                'revenue': revenue
            })
            
    # 3. Finalizar cálculo dos custos diários de publicidade com ruído realista
    for date_str, ch_data in daily_metrics.items():
        for channel in channels:
            behav = channel_behaviors[channel]
            clicks = ch_data[channel]['clicks']
            
            # Se for canal orgânico ou email direto, custo e impressão funcionam diferente
            if behav['avg_cpc'] == 0:
                impressions = 0
                spend = 0.0
            else:
                # Gerar impressões baseadas no CTR médio
                if clicks > 0:
                    impressions = int(clicks / behav['ctr'] * random.uniform(0.9, 1.1))
                    # Custo real gerado por cliques * CPC médio + ruído de mercado de leilão
                    spend = round(clicks * behav['avg_cpc'] * random.uniform(0.85, 1.15), 2)
                else:
                    impressions = random.randint(100, 500) if channel != 'Email' else 0
                    spend = 0.0
                    
            daily_ads_costs.append({
                'date': date_str,
                'channel': channel,
                'impressions': impressions,
                'clicks': clicks,
                'spend': spend
            })
            
    # Converter para DataFrames
    df_clicks = pd.DataFrame(click_records)
    df_sales = pd.DataFrame(sales_records)
    df_ads_costs = pd.DataFrame(daily_ads_costs)
    
    # Criar diretório data/ se não existir
    os.makedirs('data', exist_ok=True)
    
    # Exportar para CSV
    df_clicks.to_csv('data/raw_clicks.csv', index=False)
    df_sales.to_csv('data/raw_sales.csv', index=False)
    df_ads_costs.to_csv('data/raw_ads_costs.csv', index=False)
    
    print(f"Dados gerados com sucesso na pasta 'data/':")
    print(f"- {len(df_clicks)} registros de cliques salvos em raw_clicks.csv")
    print(f"- {len(df_sales)} registros de vendas salvos em raw_sales.csv")
    print(f"- {len(df_ads_costs)} registros de custos salvos em raw_ads_costs.csv")

if __name__ == '__main__':
    generate_synthetic_data()
