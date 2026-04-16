# 📁 Estrutura de Arquivos Criada para GitHub

Aqui estão todos os arquivos e pastas necessários para colocar seu sistema **PGM Porto Velho** no ar via GitHub + Render.

## 📂 Arquivos Criados

### 1. **templates/dashboard.html** ✅
- Dashboard responsivo com abas para:
  - 📊 Dashboard (KPIs e estatísticas)
  - 📤 Importar (upload de planilhas)
  - 🔴 Críticos (prazos vencidos)
  - 📄 Relatórios (geração de PDFs)
  - 👥 Equipe (gestão de membros)
- Design profissional com CSS puro (sem dependências)
- Compatível com mobile

### 2. **app/__init__.py** ✅
- Factory pattern do Flask
- Configuração automática do banco de dados
- Inicialização de extensões (SQLAlchemy, etc)

### 3. **app/routes.py** ✅
- Rotas principais do sistema
- Decorador `@token_required` para segurança
- Endpoints de API para:
  - `/painel` - acesso ao dashboard
  - `/api/upload` - importar planilha
  - `/api/dashboard` - dados dos KPIs
  - `/api/criticos` - prazos vencidos
  - `/api/relatorios/` - gerar PDFs
  - `/api/equipe` - gerenciar membros

### 4. **app/models.py** ✅
- Modelos SQLAlchemy prontos:
  - `Membro` - equipe
  - `Prazo` - processos e prazos
  - `Alerta` - log de alertas WhatsApp
  - `Relatorio` - PDF gerados
  - `ImportacaoLog` - histórico de importações

### 5. **.gitignore** ✅
- Padrões para não versionar:
  - `.env` (senhas e tokens)
  - `__pycache__/` e `*.pyc`
  - `venv/` (ambiente virtual)
  - `*.db` (banco de dados local)
  - `uploads/` e `relatorios/`
  - IDE config (`.vscode/`, `.idea/`)

### 6. **Procfile** ✅
- Configuração para Render.com
- Comando: `gunicorn run:app`

---

## 🚀 Como Usar no GitHub

### PASSO 1: Preparar seu repositório local

```bash
# Clone/abra o diretório do seu projeto
cd /caminho/para/pgm-relatorios

# Copie os arquivos criados para seu projeto:
# 1. Copie a pasta 'templates/' para o root do projeto
# 2. Copie '.gitignore' para o root
# 3. Copie 'Procfile' para o root
# 4. Dentro da pasta 'app/', crie ou atualize:
#    - __init__.py (copie app_init.py renomeado)
#    - routes.py (copie app_routes.py renomeado)
#    - models.py (copie app_models.py renomeado)
```

Sua estrutura deve ficar assim:

```
pgm-relatorios/
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore          ← NOVO
├── Procfile            ← NOVO
├── README.md
├── app/
│   ├── __init__.py     ← ATUALIZAR
│   ├── routes.py       ← NOVO
│   ├── models.py       ← NOVO
│   ├── parser.py       (você implementa)
│   ├── pdf_gen.py      (você implementa)
│   └── alerts.py       (você implementa)
├── templates/          ← NOVA PASTA
│   └── dashboard.html  ← NOVO
└── uploads/            (auto-criado)
```

### PASSO 2: Git local

```bash
# Inicializar git (se ainda não tiver)
git init

# Adicionar arquivos
git add .

# Commit inicial
git commit -m "Initial commit: estrutura básica com dashboard e modelos"

# Criar repositório no GitHub
# 1. Acesse https://github.com/new
# 2. Nome: pgm-relatorios
# 3. Clique Create
```

### PASSO 3: Push para GitHub

```bash
# Adicionar remote (copie o comando exato do GitHub)
git remote add origin https://github.com/SEU_USUARIO/pgm-relatorios.git
git branch -M main
git push -u origin main
```

### PASSO 4: Deploy no Render

1. **Acesse**: https://render.com
2. **Clique**: "New +" → "Web Service"
3. **Conecte seu GitHub** (authorize)
4. **Selecione**: repositório `pgm-relatorios`
5. **Configure**:
   - **Name**: `pgm-relatorios`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app --bind 0.0.0.0:$PORT`
6. **Environment Variables** (clique em "Add Environment Variable"):
   ```
   SECRET_KEY = (gere uma senha aleatória: python3 -c "import secrets; print(secrets.token_hex(32))")
   ACCESS_TOKEN = pgm-contenciosa-2026
   ENABLE_SCHEDULER = true
   ```
7. **Clique**: "Create Web Service"
8. **Aguarde**: 2-3 minutos

O Render vai gerar um link tipo: `https://pgm-relatorios.onrender.com`

### PASSO 5: Acessar o sistema

```
https://pgm-relatorios.onrender.com/painel?token=pgm-contenciosa-2026
```

---

## 📝 O que Ainda Precisa Ser Implementado

O dashboard HTML está **pronto e funcional**, mas você ainda precisa completar:

### 1. **app/parser.py** - Parser da planilha
```python
def parse_xlsx(file_stream):
    """Lê arquivo XLSX e retorna lista de Prazos"""
    # Usar openpyxl para ler o arquivo
    # Retornar lista de dicts com: numero_processo, responsavel, data_prazo, etc
```

### 2. **app/pdf_gen.py** - Gerador de PDF
```python
def gerar_relatorio_pdf(tipo, procurador=None):
    """Gera PDF usando ReportLab"""
    # Usar ReportLab para criar PDFs profissionais
    # Tipos: semanal, mensal, individual
```

### 3. **app/alerts.py** - Alertas WhatsApp
```python
def enviar_alerta_whatsapp(membro, prazo):
    """Envia alerta via Twilio"""
    # Se TWILIO_ACCOUNT_SID está preenchido, enviar de verdade
    # Se não, simular e logar no banco
```

### 4. **Integração de banco de dados**
- As rotas estão prontas, mas faltam conectar ao banco
- Exemplo em `/api/dashboard`:
```python
@bp.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard():
    from app.models import Prazo
    total = Prazo.query.count()
    vencidos = Prazo.query.filter(Prazo.status == 'vencido').count()
    # ... retornar JSON com dados reais
```

---

## 🔐 Segurança

- ✅ Token de acesso obrigatório em todas as rotas
- ✅ `.env` não é versionado (no `.gitignore`)
- ✅ Headers de segurança adicionados
- ✅ Bloqueio de indexação (SEO)
- ✅ Uploads limitados a 16MB

---

## 🆘 Dúvidas?

Consulte o arquivo **GUIA_PASSO_A_PASSO.txt** que veio com seu projeto para:
- Instalação local em Windows/Mac/Linux
- Configuração do Twilio (WhatsApp)
- Deploy em outras plataformas (Railway, VPS)

---

**Criado em**: 15 de Abril de 2026  
**Para**: Subprocuradoria Contenciosa — PGM Porto Velho
