# ✅ CHECKLIST — Colocar Sistema no GitHub + Render

## 📋 ANTES DE COMEÇAR

- [ ] Tenho conta no GitHub? (https://github.com)
- [ ] Tenho conta no Render? (https://render.com)
- [ ] Git está instalado no PC? (teste: `git --version`)
- [ ] Python e venv configurados? (teste: `python -m venv venv`)

---

## 🗂️ PASSO 1: Preparar Pasta Local (5 minutos)

```bash
# Abra prompt na pasta do projeto:
cd C:\PGM\sistema-relatorios
```

**Copie estes arquivos criados para o root do projeto:**

- [ ] Pasta `templates/` com `dashboard.html`
- [ ] Arquivo `.gitignore`
- [ ] Arquivo `Procfile`

**Dentro da pasta `app/`, crie ou atualize:**

- [ ] `__init__.py` (substitua pelo arquivo criado)
- [ ] `routes.py` (arquivo novo)
- [ ] `models.py` (arquivo novo)

**Verifique se já tem:**
- [ ] `run.py`
- [ ] `requirements.txt`
- [ ] `.env.example`
- [ ] `README.md`

---

## 🔧 PASSO 2: Testar Localmente (10 minutos)

```bash
# No prompt, na pasta do projeto:

# Ativar venv
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Criar arquivo .env (cópia do .env.example)
copy .env.example .env

# Editar .env (abra com bloco de notas)
notepad .env
# Altere SECRET_KEY e ACCESS_TOKEN

# Rodar servidor
python run.py

# No navegador:
http://localhost:5000/painel?token=seu-token-aqui
```

- [ ] Servidor rodando sem erro?
- [ ] Dashboard carregando?
- [ ] Abas (Importar, Críticos, Relatórios, Equipe) funcionando?

**Se tudo OK**, pressione Ctrl+C para parar.

---

## 📤 PASSO 3: Criar Repositório GitHub (5 minutos)

```bash
# Inicializar git (se ainda não tiver)
git init

# Adicionar todos os arquivos
git add .

# Fazer commit inicial
git commit -m "Inicial: estrutura com dashboard, modelos e rotas"

# Verificar status
git status
```

- [ ] Arquivos adicionados?
- [ ] `.env` **NÃO** aparece? (deve estar no .gitignore)
- [ ] `__pycache__`, `venv` **NÃO** aparecem?

**Se tudo OK**, vá para GitHub:

1. [ ] Acesse: https://github.com/new
2. [ ] **Repository name**: `pgm-relatorios`
3. [ ] **Description**: `Sistema de Gestão de Prazos Processuais — PGM Porto Velho`
4. [ ] **Public** (se quiser) ou **Private** (mais seguro)
5. [ ] Clique em **Create repository**

GitHub vai mostrar comandos. Execute no prompt:

```bash
git remote add origin https://github.com/SEU_USUARIO/pgm-relatorios.git
git branch -M main
git push -u origin main
```

- [ ] Push concluído?
- [ ] Repositório visível no GitHub?

---

## 🚀 PASSO 4: Deploy no Render (10 minutos)

1. [ ] Acesse: https://render.com/dashboard
2. [ ] Clique: **New +** → **Web Service**
3. [ ] **Connect GitHub account** (autorize)
4. [ ] **Selecione**: `pgm-relatorios`
5. [ ] Preencha:
   - [ ] **Name**: `pgm-relatorios`
   - [ ] **Environment**: Python 3
   - [ ] **Build Command**: `pip install -r requirements.txt`
   - [ ] **Start Command**: `gunicorn run:app --bind 0.0.0.0:$PORT`
   - [ ] **Auto-deploy**: ativado

6. [ ] Clique: **Advanced**
7. [ ] **Add Environment Variable**:
   - [ ] `SECRET_KEY` = (gere: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - [ ] `ACCESS_TOKEN` = `pgm-contenciosa-2026`
   - [ ] `ENABLE_SCHEDULER` = `true`

8. [ ] Clique: **Create Web Service**
9. [ ] **Aguarde 2-3 minutos** (amarelo = building, verde = rodando)

---

## ✨ PASSO 5: Testar em Produção (5 minutos)

Quando o Render ficar **verde**, clique no link que aparecer. Será algo como:

```
https://pgm-relatorios.onrender.com
```

Acesse:
```
https://pgm-relatorios.onrender.com/painel?token=pgm-contenciosa-2026
```

- [ ] Dashboard carrega?
- [ ] Abas funcionam?
- [ ] Design está OK?

---

## 🔄 PASSO 6: Atualizações Futuras

Toda vez que você faz alterações locais:

```bash
git add .
git commit -m "Descrição da alteração"
git push
```

Render detecta automaticamente e redeploy o sistema. ✅

---

## ⚠️ TROUBLESHOOTING

| Problema | Solução |
|----------|---------|
| 404 no dashboard | Verificar token na URL |
| `.env` aparece no GitHub | Deletar arquivo, fazer commit, atualizar `.gitignore` |
| Render com erro 500 | Ver logs em Render > Logs, verificar DATABASE_URL |
| Banco de dados vazio | Primeiro acesso cria tabelas automaticamente |
| WhatsApp não envia | Configure Twilio antes (veja GUIA_PASSO_A_PASSO.txt) |

---

## 📞 Suporte

- **Local**: Execute `python run.py` e teste em `localhost:5000`
- **Produção**: Veja logs do Render no dashboard
- **Docs**: Veja `COMO_USAR_GITHUB.md` para detalhes

---

**Tempo total esperado: ~35 minutos** ⏱️
