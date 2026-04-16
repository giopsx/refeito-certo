"""Modelos de dados (SQLAlchemy)."""
from app import db
from datetime import datetime


class Membro(db.Model):
    """Modelo para membros da equipe."""
    __tablename__ = 'membros'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    funcao = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    whatsapp = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    prazos = db.relationship('Prazo', back_populates='responsavel', lazy=True)
    alertas = db.relationship('Alerta', back_populates='membro', lazy=True)
    
    def __repr__(self):
        return f'<Membro {self.nome}>'


class Prazo(db.Model):
    """Modelo para prazos processuais."""
    __tablename__ = 'prazos'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_processo = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.String(255), nullable=False)
    data_prazo = db.Column(db.Date, nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey('membros.id'), nullable=False)
    status = db.Column(db.String(20), default='aberto')  # aberto, cumprido, vencido
    notas = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    responsavel = db.relationship('Membro', back_populates='prazos')
    alertas = db.relationship('Alerta', back_populates='prazo', lazy=True)
    
    def __repr__(self):
        return f'<Prazo {self.numero_processo}>'
    
    @property
    def dias_ate_prazo(self):
        """Calcula dias até o prazo (negativo = vencido)."""
        from datetime import date
        return (self.data_prazo - date.today()).days
    
    @property
    def esta_vencido(self):
        """Verifica se prazo está vencido."""
        return self.dias_ate_prazo < 0 and self.status != 'cumprido'


class Alerta(db.Model):
    """Modelo para registro de alertas enviados."""
    __tablename__ = 'alertas'
    
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membros.id'), nullable=False)
    prazo_id = db.Column(db.Integer, db.ForeignKey('prazos.id'), nullable=False)
    tipo = db.Column(db.String(20), default='whatsapp')  # whatsapp, email, sistema
    enviado = db.Column(db.Boolean, default=False)
    enviado_em = db.Column(db.DateTime)
    erro = db.Column(db.String(255))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    membro = db.relationship('Membro', back_populates='alertas')
    prazo = db.relationship('Prazo', back_populates='alertas')
    
    def __repr__(self):
        return f'<Alerta {self.id}>'


class Relatorio(db.Model):
    """Modelo para registrar relatórios gerados."""
    __tablename__ = 'relatorios'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # semanal, mensal, individual
    procurador_id = db.Column(db.Integer, db.ForeignKey('membros.id'))  # NULL = todos
    hash_unico = db.Column(db.String(64), unique=True, nullable=False)
    caminho_arquivo = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    procurador = db.relationship('Membro')
    
    def __repr__(self):
        return f'<Relatorio {self.tipo} {self.id}>'


class ImportacaoLog(db.Model):
    """Modelo para log de importações de planilhas."""
    __tablename__ = 'importacao_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    arquivo_nome = db.Column(db.String(255), nullable=False)
    prazos_processados = db.Column(db.Integer, default=0)
    prazos_novos = db.Column(db.Integer, default=0)
    prazos_atualizados = db.Column(db.Integer, default=0)
    sucesso = db.Column(db.Boolean, default=False)
    erro_mensagem = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ImportacaoLog {self.arquivo_nome} {self.id}>'
