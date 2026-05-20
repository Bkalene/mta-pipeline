import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Carregar variáveis de ambiente do arquivo .env local
load_dotenv()

DATABASE_URL = os.getenv("SUPABASE_DB_URL")

if not DATABASE_URL:
    raise ValueError(
        "A variável de ambiente SUPABASE_DB_URL não foi definida. "
        "Certifique-se de configurar o arquivo .env com a string de conexão do Supabase."
    )

# Configurar o Engine do SQLAlchemy
# Usamos o pool_pre_ping=True para garantir conexões resilientes com o banco em nuvem
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800
)

# Configurar a fábrica de Sessões
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarativa base para os modelos ORM
Base = declarative_base()

def get_db():
    """
    Gerenciador de contexto para obter sessões de banco de dados
    de forma segura e garantir o fechamento da conexão após o uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
