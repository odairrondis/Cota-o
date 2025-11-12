from database import db
from datetime import datetime

class Cotacao(db.Model):
    """Modelo para armazenar o histórico de cotações"""
    __tablename__ = 'cotacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    moeda = db.Column(db.String(3), nullable=False)
    nome_moeda = db.Column(db.String(100), nullable=False)
    valor_atual = db.Column(db.Float, nullable=False)
    variacao = db.Column(db.Float, nullable=False)
    timestamp_api = db.Column(db.String(50), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    def para_dict(self):
        """Converter modelo para dicionário JSON"""
        return {
            'id': self.id,
            'moeda': self.moeda,
            'nome_moeda': self.nome_moeda,
            'valor_atual': self.valor_atual,
            'variacao': self.variacao,
            'timestamp_api': self.timestamp_api,
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M:%S')
        }

class Alerta(db.Model):
    """Modelo para armazenar alertas de cotação"""
    __tablename__ = 'alertas'
    
    id = db.Column(db.Integer, primary_key=True)
    moeda = db.Column(db.String(3), nullable=False)
    valor_limite = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'maior' ou 'menor'
    ativo = db.Column(db.Boolean, default=True)
    disparado = db.Column(db.Boolean, default=False)  # ✅ NOVO CAMPO
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    disparado_em = db.Column(db.DateTime, nullable=True)  # ✅ NOVO CAMPO
    
    def para_dict(self):
        return {
            'id': self.id,
            'moeda': self.moeda,
            'valor_limite': self.valor_limite,
            'tipo': self.tipo,
            'ativo': self.ativo,
            'disparado': self.disparado,
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M:%S'),
            'disparado_em': self.disparado_em.strftime('%d/%m/%Y %H:%M:%S') if self.disparado_em else None
        }