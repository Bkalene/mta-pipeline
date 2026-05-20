import os
import pandas as pd
from sqlalchemy import Column, String, Integer, Float, DateTime, Date, ForeignKey
from src.database import Base, engine, SessionLocal

# ==========================================
# 1. Definição do Esquema de Tabelas (Modelos ORM)
# ==========================================

class AdsCosts(Base):
    __tablename__ = 'ads_costs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    channel = Column(String(50), nullable=False)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0.0)

class Clicks(Base):
    __tablename__ = 'clicks'
    
    click_id = Column(String(50), primary_key=True)
    cookie_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    channel = Column(String(50), nullable=False)

class Sales(Base):
    __tablename__ = 'sales'
    
    sale_id = Column(String(50), primary_key=True)
    cookie_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    revenue = Column(Float, nullable=False)

# ==========================================
# 2. Funções de Ingestão e Processamento
# ==========================================

def init_db():
    """
    Cria as tabelas no Supabase (PostgreSQL) com base na declaração de modelos do SQLAlchemy.
    """
    print("Inicializando criação de tabelas no Supabase...")
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")

def ingest_raw_data(data_dir='data'):
    """
    Lê os arquivos CSV locais do diretório e insere as informações no Supabase.
    """
    db = SessionLocal()
    try:
        # Verificar arquivos
        required_files = ['raw_clicks.csv', 'raw_sales.csv', 'raw_ads_costs.csv']
        for file in required_files:
            if not os.path.exists(os.path.join(data_dir, file)):
                raise FileNotFoundError(
                    f"Arquivo {file} não encontrado na pasta {data_dir}. "
                    "Execute o gerador de dados (data_generator.py) primeiro."
                )

        print("\n--- Iniciando Ingestão de Dados ---")

        # 1. Ingestão de Custos de Campanhas (ads_costs)
        print("Lendo e limpando dados de custos de anúncios...")
        df_costs = pd.read_csv(os.path.join(data_dir, 'raw_ads_costs.csv'))
        df_costs['date'] = pd.to_datetime(df_costs['date']).dt.date
        
        # Limpar registros anteriores da tabela de custos para evitar duplicidade
        db.query(AdsCosts).delete()
        db.commit()
        
        # Inserção em bloco (Bulk Insert) usando pandas
        df_costs.to_sql('ads_costs', con=engine, if_exists='append', index=False)
        print(f"-> {len(df_costs)} registros de custos inseridos.")

        # 2. Ingestão de Cliques de Usuários (clicks)
        print("Lendo e limpando dados de cliques...")
        df_clicks = pd.read_csv(os.path.join(data_dir, 'raw_clicks.csv'))
        df_clicks['timestamp'] = pd.to_datetime(df_clicks['timestamp'])
        
        # Limpar registros anteriores da tabela de cliques
        db.query(Clicks).delete()
        db.commit()
        
        df_clicks.to_sql('clicks', con=engine, if_exists='append', index=False)
        print(f"-> {len(df_clicks)} registros de cliques inseridos.")

        # 3. Ingestão de Vendas (sales)
        print("Lendo e limpando dados de vendas...")
        df_sales = pd.read_csv(os.path.join(data_dir, 'raw_sales.csv'))
        df_sales['timestamp'] = pd.to_datetime(df_sales['timestamp'])
        
        # Limpar registros anteriores da tabela de vendas
        db.query(Sales).delete()
        db.commit()
        
        df_sales.to_sql('sales', con=engine, if_exists='append', index=False)
        print(f"-> {len(df_sales)} registros de vendas inseridos.")

        print("\n=== Ingestão concluída com sucesso! ===")

    except Exception as e:
        db.rollback()
        print(f"Erro durante a ingestão de dados: {e}")
        raise e
    finally:
        db.close()

if __name__ == '__main__':
    # Inicializa as tabelas no banco de dados e executa a ingestão inicial
    init_db()
    ingest_raw_data()
