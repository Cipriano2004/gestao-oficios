# Gestão de Ofícios

[![CI](https://github.com/Cipriano2004/gestao-oficios/actions/workflows/ci.yml/badge.svg)](https://github.com/Cipriano2004/gestao-oficios/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-3.1-000000?logo=flask)
![MySQL](https://img.shields.io/badge/mysql-8%20%7C%20MariaDB-4479A1?logo=mysql&logoColor=white)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

Sistema web que automatiza a criação, a numeração e o acompanhamento de ofícios de um gabinete legislativo municipal. Gera o documento Word pronto para assinatura, controla a numeração anual sem números repetidos, mostra indicadores e gráficos para reuniões e registra cada ação em uma trilha de auditoria.

![Dashboard](docs/screenshots/dashboard-claro.png)

## Contexto

Trabalhando em um gabinete de vereador, eu redigia ofícios no Word a partir de textos copiados de documentos antigos e controlava a numeração à mão. Isso gerava retrabalho, números duplicados e nenhuma visão de quantos pedidos cada secretaria tinha recebido ou se já tinham sido atendidos.

Por iniciativa própria, desenvolvi a **versão 1**: um sistema Flask com SQLite, de uso pessoal, rodando só no meu computador, que gerava os ofícios a partir de modelos com campos automáticos e montava gráficos e resumos para as reuniões.

Esta **versão 2** é a reestruturação completa do projeto, pensando em uso por uma equipe:

| | v1 (uso pessoal) | v2 (este repositório) |
|---|---|---|
| Banco | SQLite em arquivo | **MySQL / MariaDB** com migrações (Alembic) |
| Código | um `app.py` de 2.100 linhas | *application factory*, **blueprints** e **camada de serviços** |
| Acesso | sem login | **login, perfis de acesso e trilha de auditoria** |
| Numeração | calculada em Python | **transacional** (`SELECT ... FOR UPDATE` + `UNIQUE`), testada com usuários simultâneos |
| Interface | Bootstrap padrão | painel com sidebar, **modo escuro**, assistente em etapas, responsivo |
| Qualidade | sem testes automatizados | **60 testes**, lint e CI com MySQL |
| Execução | `python app.py` | **Docker Compose** ou XAMPP |

## Funcionalidades

- **Assistente de novo ofício em 4 etapas**: destino → dados do atendimento → texto → revisão em formato de folha A4.
- **Modelos com placeholders** (`[ENDEREÇO]`, `[BAIRRO]`, `[MUNICIPE_NOME]`, `[DATA_EVENTO]`…) preenchidos automaticamente.
- **Documento Word** gerado na hora do download, no layout oficial (Arial 12, número, data por extenso, assinatura).
- **Numeração anual automática** (`001/2026`), com reserva de números usados fora do sistema, ajuste do próximo número e mapa visual do ano.
- **Dashboard** com indicadores do mês, série de 12 meses, situação executado × pendente e últimos ofícios.
- **Gráficos por secretaria e por assessor** com detalhamento ao clicar; nomes de assessor escritos de formas diferentes são agrupados.
- **Fechamento mensal** com resumo em texto para reuniões, gráficos e versão para impressão/PDF.
- **Busca, filtros e paginação**; exportação filtrada para **Excel**.
- **Administração de usuários** e **trilha de auditoria** com filtros e alerta de falhas de login.

## Segurança

Como o sistema lida com dados pessoais de munícipes (nome, telefone e endereço), a segurança foi tratada como requisito, com referência ao **OWASP Top 10** e à **LGPD**.

| Controle | Implementação | Referência |
|---|---|---|
| Autenticação | Flask-Login; senha com hash **scrypt**; mensagem de erro genérica (não revela se o e-mail existe) | OWASP A07 |
| Força bruta | **Limite de 5 tentativas/minuto** no login (Flask-Limiter); cada falha é auditada com IP | OWASP A07 |
| Autorização | Perfis **admin / assessor / somente leitura** checados no servidor em cada rota | OWASP A01 |
| CSRF | Token em todos os formulários e no `fetch` do JavaScript (Flask-WTF) | OWASP A01 |
| Métodos seguros | Exclusões e logout aceitam **somente POST**, com confirmação | OWASP A01 |
| Open redirect | `?next=` só aceita caminhos internos | OWASP A01 |
| Injeção | Somente ORM / consultas parametrizadas; validação de entrada | OWASP A03 |
| Cabeçalhos | **CSP** sem script inline nem CDN (`script-src 'self'`), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy` | OWASP A05 |
| Sessão | Cookies `HttpOnly` e `SameSite=Lax`; `Secure` configurável; expiração em 8 h | OWASP A07 |
| Configuração | `SECRET_KEY` e banco **obrigatórios via `.env`** (o sistema não sobe sem eles); `DEBUG` desligado em produção | OWASP A05 |
| Auditoria | Tabela `log_auditoria`: quem, o quê, quando, IP e user-agent; tela com filtros | Rastreabilidade |
| Menor privilégio | Usuário MySQL dedicado só ao banco do sistema; container roda sem root; banco não exposto fora do Docker | Hardening |
| Dados pessoais | Nenhum `.docx` fica salvo em pasta pública (gerado em memória); repositório só com dados fictícios | LGPD |

Todos esses controles têm teste automatizado em [`tests/test_seguranca.py`](tests/test_seguranca.py).

![Trilha de auditoria](docs/screenshots/auditoria.png)

## Telas

| Novo ofício | Revisão e documento |
|---|---|
| ![Novo ofício](docs/screenshots/novo-oficio.png) | ![Detalhe](docs/screenshots/detalhe.png) |

| Lista com filtros | Numeração do ano |
|---|---|
| ![Ofícios](docs/screenshots/oficios.png) | ![Numeração](docs/screenshots/numeracao.png) |

| Gráficos com detalhamento | Fechamento mensal |
|---|---|
| ![Gráficos](docs/screenshots/graficos-detalhe.png) | ![Fechamento](docs/screenshots/fechamento.png) |

| Modo escuro | Celular |
|---|---|
| ![Modo escuro](docs/screenshots/dashboard-escuro.png) | <img src="docs/screenshots/celular.png" width="260" alt="Celular"> |

## Arquitetura

```mermaid
flowchart LR
    U[Navegador] -->|HTTPS| W[Waitress]
    W --> B
    subgraph F[Flask · application factory]
        B[Blueprints<br/>auth · oficios · modelos<br/>numeracao · relatorios · admin · api]
        S[Serviços<br/>numeração · placeholders<br/>documento Word · relatórios · auditoria]
        B --> S
    end
    S --> DB[(MySQL / MariaDB)]
    S --> D[python-docx · openpyxl]
```

```
app/
├── __init__.py          # create_app(): extensões, blueprints, cabeçalhos de segurança, erros
├── config.py            # configuração por ambiente lida do .env
├── seguranca.py         # login obrigatório e permissões por perfil
├── models/              # Usuario, Oficio, TemplateOficio, Departamento, Numeração, LogAuditoria
├── services/            # regras de negócio, sem dependência de request (testáveis)
├── blueprints/          # rotas finas: validam, chamam serviços, renderizam
├── templates/           # Jinja2: layout, componentes e uma pasta por área
└── static/              # CSS do tema, JS e bibliotecas locais (Bootstrap, Chart.js, Inter)
migrations/              # Alembic (Flask-Migrate)
scripts/                 # migração do banco antigo (SQLite → MySQL)
tests/                   # pytest: serviços, rotas, segurança e concorrência
```

### Modelo de dados

```mermaid
erDiagram
    USUARIO ||--o{ OFICIO : cria
    USUARIO ||--o{ LOG_AUDITORIA : gera
    DEPARTAMENTO ||--o{ SECRETARIO : possui
    DEPARTAMENTO ||--o{ TEMPLATE_OFICIO : possui
    DEPARTAMENTO ||--o{ OFICIO : recebe
    SECRETARIO ||--o{ OFICIO : "é destinatário"
    OFICIO {
        string numero UK "001/2026"
        int ano "UNIQUE(ano, sequencial)"
        int sequencial
        bool executado
    }
    NUMERACAO_CONFIG {
        int ano UK "linha usada como trava"
        int offset "próximo número desejado"
    }
    NUMERO_RESERVA {
        int ano "UNIQUE(ano, sequencial)"
        int sequencial
    }
```

### Como a numeração evita números repetidos

1. A requisição trava a linha do ano em `numeracao_config` com `SELECT ... FOR UPDATE`; as outras esperam na fila.
2. Calcula o próximo número livre, pulando números reservados e respeitando o ajuste manual.
3. Insere o ofício e faz `COMMIT`, liberando a trava. A restrição `UNIQUE(ano, sequencial)` é a última garantia: em caso de conflito, a operação é refeita.

O banco usa isolamento `READ COMMITTED` para que cada consulta enxergue o último número confirmado. O teste [`test_concorrencia.py`](tests/test_concorrencia.py) dispara 12 usuários simultâneos criando 60 ofícios e confere que os números saem de 1 a 60, sem buracos nem repetições.

## Como rodar

### Opção A: Docker Compose (recomendado)

Pré-requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone https://github.com/Cipriano2004/gestao-oficios.git
cd gestao-oficios
cp .env.example .env          # no Windows: copy .env.example .env
```

Edite o `.env`: gere a `SECRET_KEY` com `python -c "import secrets; print(secrets.token_hex(32))"` e troque `MYSQL_PASSWORD` e `MYSQL_ROOT_PASSWORD`. Depois:

```bash
docker compose up --build -d
docker compose exec app flask seed          # dados FICTÍCIOS de demonstração (opcional)
docker compose exec app flask criar-admin   # cria o primeiro usuário
```

Acesse **http://localhost:8000**. As migrações rodam sozinhas quando o container sobe.

### Opção B: XAMPP (sem Docker)

1. Abra o XAMPP e inicie o **MySQL**.
2. Em `http://localhost/phpmyadmin`, aba **SQL**:
   ```sql
   CREATE DATABASE gestao_oficios CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'oficios_app'@'localhost' IDENTIFIED BY 'TroqueEstaSenha';
   GRANT ALL PRIVILEGES ON gestao_oficios.* TO 'oficios_app'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. No terminal, na pasta do projeto (Python 3.11+):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   copy .env.example .env            # ajuste SECRET_KEY e a senha no DATABASE_URL
   flask db upgrade
   flask seed                        # opcional: dados fictícios
   flask criar-admin
   python run.py                     # http://127.0.0.1:8000
   ```

### Trazendo dados da versão antiga

```bash
flask db upgrade
python scripts/migrar_sqlite_para_mysql.py caminho/para/gestao_oficios.db
```

O script copia secretarias, secretários, modelos, reservas, configuração de numeração e ofícios, convertendo os números para o formato `ano + sequencial`.

## Testes e qualidade

```bash
pip install -r requirements-dev.txt
pytest --cov=app                  # SQLite em memória
ruff check .
```

Para rodar contra MySQL (incluindo o teste de concorrência), defina `TEST_DATABASE_URL`:

```bash
TEST_DATABASE_URL="mysql+pymysql://usuario:senha@127.0.0.1:3306/gestao_oficios_test?charset=utf8mb4" pytest
```

O [CI](.github/workflows/ci.yml) roda a cada push: lint, migrações do zero (upgrade e downgrade), testes em MySQL 8 e SQLite com Python 3.11 e 3.12, e build da imagem Docker.

## Stack

**Backend:** Python, Flask 3, SQLAlchemy 2, Flask-Migrate (Alembic), Flask-Login, Flask-WTF, Flask-Limiter, PyMySQL
**Banco:** MySQL 8 / MariaDB
**Documentos:** python-docx, openpyxl
**Frontend:** Jinja2, Bootstrap 5.3, Bootstrap Icons, Chart.js 4, fonte Inter (todos servidos localmente)
**Infra e qualidade:** Docker, Docker Compose, Waitress, pytest, ruff, GitHub Actions

## Próximos passos

- Anexar o documento assinado (PDF) ao ofício e registrar a data de protocolo na secretaria.
- Autenticação em dois fatores (TOTP) para administradores.
- Envio dos logs de auditoria para um SIEM (ex.: Wazuh) via syslog.
- Notificação por e-mail dos ofícios pendentes há mais de 30 dias.

## Autor

**Ariel Cipriano do Nascimento**
[LinkedIn](https://www.linkedin.com/in/ariel-cipriano) · arielcipra2004@gmail.com

---

Todos os nomes, endereços e telefones das imagens e do comando `flask seed` são **fictícios**, gerados com a biblioteca Faker.
