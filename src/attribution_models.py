import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from src.database import engine

def fetch_data_from_db():
    """
    Carrega os dados de cliques, vendas e custos do Supabase.
    """
    df_clicks = pd.read_sql("SELECT * FROM clicks", con=engine)
    df_sales = pd.read_sql("SELECT * FROM sales", con=engine)
    df_costs = pd.read_sql("SELECT * FROM ads_costs", con=engine)
    
    # Converter colunas de data/timestamp
    df_clicks['timestamp'] = pd.to_datetime(df_clicks['timestamp'])
    df_sales['timestamp'] = pd.to_datetime(df_sales['timestamp'])
    
    return df_clicks, df_sales, df_costs

# ==========================================
# 1. Modelos Baseados em Regras Tradicionais
# ==========================================

def calculate_rules_based_attribution(df_clicks, df_sales):
    """
    Calcula atribuição de vendas e receitas para First Touch, Last Touch e Linear.
    """
    # Ordenar cliques por tempo
    df_clicks = df_clicks.sort_values(by=['cookie_id', 'timestamp'])
    
    # 1. Identificar jornadas de usuários que resultaram em vendas
    # Associar cada venda aos cliques que ocorreram ANTES da data da venda para o mesmo cookie_id
    journeys = []
    
    for _, sale in df_sales.iterrows():
        user_clicks = df_clicks[
            (df_clicks['cookie_id'] == sale['cookie_id']) & 
            (df_clicks['timestamp'] < sale['timestamp'])
        ]
        
        if len(user_clicks) > 0:
            click_list = user_clicks['channel'].tolist()
            journeys.append({
                'sale_id': sale['sale_id'],
                'cookie_id': sale['cookie_id'],
                'revenue': sale['revenue'],
                'path': click_list
            })
            
    df_journeys = pd.DataFrame(journeys)
    
    if len(df_journeys) == 0:
        return pd.DataFrame()
        
    # Inicializar dicionários de atribuição
    channels = df_clicks['channel'].unique()
    attribution = {ch: {'first_touch_rev': 0.0, 'last_touch_rev': 0.0, 'linear_rev': 0.0,
                        'first_touch_conv': 0, 'last_touch_conv': 0, 'linear_conv': 0.0} 
                   for ch in channels}
    
    # Aplicar regras de atribuição para cada venda
    for _, row in df_journeys.iterrows():
        path = row['path']
        rev = row['revenue']
        
        # First Touch
        first_ch = path[0]
        attribution[first_ch]['first_touch_rev'] += rev
        attribution[first_ch]['first_touch_conv'] += 1
        
        # Last Touch
        last_ch = path[-1]
        attribution[last_ch]['last_touch_rev'] += rev
        attribution[last_ch]['last_touch_conv'] += 1
        
        # Linear
        unique_path = path # Mantém repetições de cliques se clicou várias vezes
        num_clicks = len(unique_path)
        fractional_rev = rev / num_clicks
        fractional_conv = 1.0 / num_clicks
        for ch in unique_path:
            attribution[ch]['linear_rev'] += fractional_rev
            attribution[ch]['linear_conv'] += fractional_conv
            
    # Formatar como DataFrame
    df_attr = pd.DataFrame.from_dict(attribution, orient='index').reset_index()
    df_attr.rename(columns={'index': 'channel'}, inplace=True)
    return df_attr

# ==========================================
# 2. Modelo Baseado em Cadeias de Markov
# ==========================================

def calculate_markov_attribution(df_clicks, df_sales):
    """
    Constrói a matriz de transição de Markov e calcula o Removal Effect (Efeito de Remoção)
    para atribuir conversões aos canais de marketing.
    """
    # 1. Identificar todos os cookies de usuários e agrupá-los em caminhos (jornadas)
    df_clicks = df_clicks.sort_values(by=['cookie_id', 'timestamp'])
    
    # Mapear cookies que converteram
    converted_cookies = set(df_sales['cookie_id'].unique())
    cookie_revenues = df_sales.set_index('cookie_id')['revenue'].to_dict()
    
    paths = []
    
    # Agrupar cliques por cookie_id
    grouped_clicks = df_clicks.groupby('cookie_id')
    
    for cookie_id, group in grouped_clicks:
        channels_in_path = group['channel'].tolist()
        
        if cookie_id in converted_cookies:
            # Caminho de Sucesso
            paths.append(['Start'] + channels_in_path + ['Conversion'])
        else:
            # Caminho de Fracasso (Sem Conversão)
            paths.append(['Start'] + channels_in_path + ['No-Conversion'])
            
    # 2. Calcular frequências de transição entre estados
    transition_counts = {}
    
    for path in paths:
        for i in range(len(path) - 1):
            state_from = path[i]
            state_to = path[i+1]
            
            if state_from not in transition_counts:
                transition_counts[state_from] = {}
            if state_to not in transition_counts[state_from]:
                transition_counts[state_from][state_to] = 0
                
            transition_counts[state_from][state_to] += 1
            
    # 3. Construir Matriz de Probabilidade de Transição (Dicionário)
    transition_matrix = {}
    for state_from, transitions in transition_counts.items():
        total_transitions = sum(transitions.values())
        transition_matrix[state_from] = {
            state_to: count / total_transitions for state_to, count in transitions.items()
        }
        
    # Os estados Conversion e No-Conversion são absorventes (só transitam para eles mesmos)
    transition_matrix['Conversion'] = {'Conversion': 1.0}
    transition_matrix['No-Conversion'] = {'No-Conversion': 1.0}
    
    # 4. Calcular Probabilidade de Conversão Geral do Sistema Base (Sem alterações)
    all_channels = list(df_clicks['channel'].unique())
    
    def calculate_total_conversion_probability(matrix):
        """
        Calcula a probabilidade de ir do estado 'Start' para 'Conversion'
        usando álgebra matricial para cadeias de Markov absorventes.
        Matriz de Transição P formatada em estados transitórios (Q) e absorventes (R).
        """
        states = sorted(list(matrix.keys()))
        absorbent_states = ['Conversion', 'No-Conversion']
        transient_states = [s for s in states if s not in absorbent_states]
        
        if not transient_states:
            return 0.0
            
        # Tamanhos
        num_transient = len(transient_states)
        
        # Mapear estados para índices matriciais
        state_idx = {state: i for i, state in enumerate(transient_states)}
        
        # Criar matriz Q (transiente para transiente)
        Q = np.zeros((num_transient, num_transient))
        # Criar matriz R (transiente para absorvente: [Conversion, No-Conversion])
        R = np.zeros((num_transient, 2))
        
        for state_from in transient_states:
            idx_from = state_idx[state_from]
            if state_from in matrix:
                for state_to, prob in matrix[state_from].items():
                    if state_to in transient_states:
                        Q[idx_from, state_idx[state_to]] = prob
                    elif state_to == 'Conversion':
                        R[idx_from, 0] = prob
                    elif state_to == 'No-Conversion':
                        R[idx_from, 1] = prob
                        
        # Matriz Fundamental F = (I - Q)^-1
        try:
            I = np.identity(num_transient)
            F = np.linalg.inv(I - Q)
            # Matriz de Absorção B = F * R
            B = np.dot(F, R)
            
            # A probabilidade de conversão partindo do estado 'Start'
            start_idx = state_idx['Start']
            conversion_prob = B[start_idx, 0]
            return conversion_prob
        except np.linalg.LinAlgError:
            # Fallback para o caso de matriz singular (divisão por zero)
            return 0.0

    base_conv_prob = calculate_total_conversion_probability(transition_matrix)
    
    # 5. Calcular o Removal Effect para cada canal
    removal_effects = {}
    
    for channel in all_channels:
        # Criar uma cópia da matriz de transição
        modified_matrix = {s_from: dict(s_to_dict) for s_from, s_to_dict in transition_matrix.items()}
        
        # Simular a remoção do canal: todas as transições que iam para o canal
        # agora vão para o estado de falha 'No-Conversion'
        for s_from in modified_matrix.keys():
            if s_from in ['Conversion', 'No-Conversion']:
                continue
            if channel in modified_matrix[s_from]:
                prob_to_channel = modified_matrix[s_from][channel]
                del modified_matrix[s_from][channel]
                # Redirecionar probabilidade para 'No-Conversion'
                modified_matrix[s_from]['No-Conversion'] = modified_matrix[s_from].get('No-Conversion', 0.0) + prob_to_channel
                
        # Calcular nova probabilidade de conversão com o canal removido
        modified_conv_prob = calculate_total_conversion_probability(modified_matrix)
        
        # Efeito de remoção: RE = (P_base - P_modificada) / P_base
        if base_conv_prob > 0:
            removal_effects[channel] = (base_conv_prob - modified_conv_prob) / base_conv_prob
        else:
            removal_effects[channel] = 0.0
            
    # Se todos os removal effects forem zero, distribui igualmente
    total_re = sum(removal_effects.values())
    if total_re == 0:
        total_re = 1.0
        removal_effects = {ch: 1.0 / len(all_channels) for ch in all_channels}
        
    # 6. Atribuir conversões e receitas reais com base na proporção do Removal Effect
    total_conversions = len(df_sales)
    total_revenue = df_sales['revenue'].sum()
    
    markov_attribution = []
    for channel in all_channels:
        re_ratio = removal_effects[channel] / sum(removal_effects.values())
        attributed_conv = total_conversions * re_ratio
        attributed_rev = total_revenue * re_ratio
        
        markov_attribution.append({
            'channel': channel,
            'markov_conv': round(attributed_conv, 2),
            'markov_rev': round(attributed_rev, 2)
        })
        
    return pd.DataFrame(markov_attribution)

# ==========================================
# 3. Consolidação Final e Métricas Financeiras
# ==========================================

def get_attribution_report():
    """
    Função principal que busca dados, calcula todos os modelos
    e consolida os resultados em um único DataFrame com custos de aquisição e ROAS.
    """
    df_clicks, df_sales, df_costs = fetch_data_from_db()
    
    if len(df_clicks) == 0 or len(df_sales) == 0:
        return pd.DataFrame()
        
    # 1. Calcular atribuição de regras e Markov
    df_rules = calculate_rules_based_attribution(df_clicks, df_sales)
    df_markov = calculate_markov_attribution(df_clicks, df_sales)
    
    # Mesclar resultados
    df_report = pd.merge(df_rules, df_markov, on='channel', how='outer')
    
    # 2. Agregar custos e cliques totais declarados por canal no banco
    df_costs_agg = df_costs.groupby('channel').agg({
        'spend': 'sum',
        'clicks': 'sum',
        'impressions': 'sum'
    }).reset_index()
    
    # Unir dados de custo ao relatório
    df_report = pd.merge(df_report, df_costs_agg, on='channel', how='left')
    df_report.fillna(0.0, inplace=True)
    
    # 3. Adicionar métricas derivadas de negócio por modelo (ROAS e CAC)
    # ROAS = Receita Atribuída / Custo
    # CAC = Custo / Conversões Atribuídas
    for prefix in ['first_touch', 'last_touch', 'linear', 'markov']:
        # Receita
        rev_col = f'{prefix}_rev'
        # Conversões
        conv_col = f'{prefix}_conv'
        
        # Calcular ROAS
        df_report[f'{prefix}_roas'] = np.where(
            df_report['spend'] > 0,
            df_report[rev_col] / df_report['spend'],
            0.0
        ).round(2)
        
        # Calcular CAC
        df_report[f'{prefix}_cac'] = np.where(
            df_report[conv_col] > 0,
            df_report['spend'] / df_report[conv_col],
            0.0
        ).round(2)
        
    return df_report

if __name__ == '__main__':
    # Teste rápido de extração local (só funciona se conectado ao Supabase)
    try:
        df = get_attribution_report()
        print(df)
    except Exception as e:
        print(f"Não foi possível rodar o relatório localmente: {e}")
