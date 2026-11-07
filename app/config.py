"""Configurações por ambiente. Tudo que é sensível vem de variáveis de ambiente (.env)."""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Sessão e cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(hours=8)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Proteção CSRF (Flask-WTF)
    WTF_CSRF_TIME_LIMIT = None

    # Limite de requisições (Flask-Limiter)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # Dados do gabinete usados nos documentos
    GABINETE_NOME = os.environ.get("GABINETE_NOME", "Gabinete Exemplo")
    CIDADE = os.environ.get("CIDADE", "Cidade Exemplo")
    RESPONSAVEL_NOME = os.environ.get("RESPONSAVEL_NOME", "NOME DO VEREADOR")
    RESPONSAVEL_CARGO = os.environ.get("RESPONSAVEL_CARGO", "Vereador")
    NUMERACAO_INICIAL = int(os.environ.get("NUMERACAO_INICIAL", "1"))

    ITENS_POR_PAGINA = 25


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "chave-apenas-para-testes"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = True
    GABINETE_NOME = "Gabinete Teste"
    CIDADE = "Cidade Teste"
    RESPONSAVEL_NOME = "FULANO DE TAL"
    RESPONSAVEL_CARGO = "Vereador"
    NUMERACAO_INICIAL = 1


CONFIGS = {
    "development": DevConfig,
    "production": ProdConfig,
    "testing": TestConfig,
}
