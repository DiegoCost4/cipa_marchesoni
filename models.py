from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

db = SQLAlchemy()

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Número do candidato (gerado aleatoriamente ou manual)
    number = db.Column(db.Integer, unique=True, nullable=False)
    department = db.Column(db.String(50))
    votes_count = db.Column(db.Integer, default=0)

    @staticmethod
    def generate_unique_number():
        while True:
            num = random.randint(10, 99)  # Números de 2 dígitos
            if not Candidate.query.filter_by(number=num).first():
                return num

class VoterLog(db.Model):
    """
    Tabela de Auditoria: Registra QUEM votou e a evidência (foto),
    mas NÃO em quem a pessoa votou, garantindo o sigilo da CIPA.
    """
    __tablename__ = 'voter_logs'
    id = db.Column(db.Integer, primary_key=True)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    photo_path = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- NOVA TABELA ---
class Employee(db.Model):
    __tablename__ = 'employees'
    cpf = db.Column(db.String(14), primary_key=True) # CPF será a chave primária
    name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100))
    role = db.Column(db.String(100)) # Cargo
    active = db.Column(db.Boolean, default=True) # Baseado na coluna SITUACAO