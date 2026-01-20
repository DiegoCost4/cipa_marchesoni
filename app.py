import os
import csv
import base64
from flask import Flask, render_template, request, jsonify
from models import db, Candidate, VoterLog, Employee
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# Senha simples (sem caracteres especiais)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/cipa_marchesoni'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'segredo_marchesoni_2026'

db.init_app(app)

# Função para garantir que existe o candidato BRANCO
def init_voting_data():
    # Cria tabelas se não existirem
    db.create_all()
    
    # Cria pasta de uploads
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Verifica se já existe o candidato "Voto em Branco" (Número 0)
    if not Candidate.query.filter_by(number=0).first():
        print("Criando opção de Voto em Branco...")
        # Depto "-" para ficar discreto no admin
        white_vote = Candidate(name="VOTO EM BRANCO", department="-", number=0)
        db.session.add(white_vote)
        db.session.commit()

# Executa a inicialização
with app.app_context():
    init_voting_data()
    
# Criar tabelas e pastas ao iniciar
with app.app_context():
    db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

# --- ROTAS DA URNA (FRONTEND) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    cpf = data.get('cpf')
    candidate_number = data.get('number')
    photo_data = data.get('photo')

    if not all([cpf, candidate_number, photo_data]):
        return jsonify({'error': 'Dados incompletos'}), 400

    cpf_clean = "".join(filter(str.isdigit, cpf))

    # 1. Verificar se já votou
    if VoterLog.query.filter_by(cpf=cpf_clean).first():
        return jsonify({'error': 'CPF já registrou voto.'}), 403

    # 2. Verificar candidato
    candidate = Candidate.query.filter_by(number=candidate_number).first()
    if not candidate:
        return jsonify({'error': 'Número de candidato inválido'}), 404

    try:
        # 3. Salvar Foto
        header, encoded = photo_data.split(",", 1)
        file_ext = header.split(';')[0].split('/')[1]
        filename = secure_filename(f"{cpf_clean}_{candidate_number}.{file_ext}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(encoded))

        # 4. Registrar Voto
        new_log = VoterLog(cpf=cpf_clean, photo_path=filename)
        db.session.add(new_log)
        
        candidate.votes_count += 1
        db.session.commit()
        
        return jsonify({'success': True, 'candidate_name': candidate.name})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/candidate-info/<int:number>')
def candidate_info(number):
    candidate = Candidate.query.filter_by(number=number).first()
    if candidate:
        return jsonify({'name': candidate.name, 'department': candidate.department})
    return jsonify({'error': 'Não encontrado'}), 404

# --- ROTAS DE API (Validações) ---

@app.route('/api/check-cpf/<cpf>')
def check_cpf(cpf):
    cpf_clean = "".join(filter(str.isdigit, cpf))
    
    # Se base vazia, libera para teste. Se tiver dados, valida.
    if Employee.query.count() > 0:
        employee = Employee.query.filter_by(cpf=cpf_clean).first()
        
        if not employee:
            return jsonify({'allowed': False, 'message': 'CPF não encontrado na base de colaboradores.'})
        
        if not employee.active:
            return jsonify({'allowed': False, 'message': 'Colaborador consta como INATIVO.'})
        
        nome_retorno = employee.name
    else:
        nome_retorno = "Colaborador (Base vazia)"

    if VoterLog.query.filter_by(cpf=cpf_clean).first():
        return jsonify({'allowed': False, 'message': f'Voto já registrado anteriormente.'})
    
    return jsonify({
        'allowed': True, 
        'message': f'Olá, {nome_retorno}. Votação Habilitada.',
        'name': nome_retorno
    })

@app.route('/api/get-employee/<cpf>')
def get_employee(cpf):
    cpf_clean = "".join(filter(str.isdigit, cpf))
    emp = Employee.query.filter_by(cpf=cpf_clean).first()
    if emp:
        return jsonify({'found': True, 'name': emp.name, 'department': emp.department})
    return jsonify({'found': False})

# --- ÁREA ADMINISTRATIVA ---

@app.route('/admin/import-csv', methods=['POST'])
def import_csv():
    file_path = os.path.join('data', 'colaboradores.csv')
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'Arquivo não encontrado!'}), 404

    try:
        Employee.query.delete() # Limpa base antiga
        
        # USA LATIN-1 (Confirmado pelo teste)
        with open(file_path, newline='', encoding='latin-1') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            count = 0
            
            for row in reader:
                # Limpeza robusta do CPF
                raw_cpf = row.get('CPF', '').replace('.', '').replace('-', '').strip()
                
                if raw_cpf and raw_cpf.isdigit():
                    situacao = row.get('SITUACAO', '').lower()
                    is_active = 'ativo' in situacao
                    
                    employee = Employee(
                        cpf=raw_cpf,
                        name=row.get('NOME', '').strip().title(),
                        department=row.get('SETOR', 'Não Informado').strip(),
                        role=row.get('CARGO', '').strip(),
                        active=is_active
                    )
                    db.session.add(employee)
                    count += 1
            
            db.session.commit()
            return jsonify({'success': True, 'message': f'{count} colaboradores importados com sucesso!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Erro no import: {str(e)}"}), 500

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Cadastro de Candidato
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['department']
        number = Candidate.generate_unique_number()
        new_c = Candidate(name=name, department=dept, number=number)
        db.session.add(new_c)
        db.session.commit()
        
    candidates = Candidate.query.order_by(Candidate.votes_count.desc()).all()
    logs = VoterLog.query.order_by(VoterLog.timestamp.desc()).all()
    
    # --- CÁLCULO DAS ESTATÍSTICAS ---
    total_employees = Employee.query.filter_by(active=True).count()
    total_votes = VoterLog.query.count()
    missing = max(0, total_employees - total_votes)
    percentage = (total_votes / total_employees * 100) if total_employees > 0 else 0
    
    stats = {
        'total': total_employees,
        'votes': total_votes,
        'missing': missing,
        'percent': round(percentage, 1)
    }

    return render_template('admin.html', candidates=candidates, logs=logs, stats=stats)

if __name__ == '__main__':
    app.run(debug=True, port=5000)