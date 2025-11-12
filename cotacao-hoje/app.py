from flask import Flask, render_template, request, redirect
from cotacao_service import CotacaoService
from database import db, init_db
from models import Alerta
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cotacao_hoje.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar banco de dados
init_db(app)

# Instanciar o serviço de cotações
cotacao_service = CotacaoService()

# Armazenar o estado da aplicação
estado_app = {
    "cotacoes": None,
    "erro": None,
    "atualizado_em": None,
    "total_buscas": 0,
    "alertas_disparados": []  # ✅ NOVO
}

def atualizar_cotacoes_periodicamente():
    """Thread que atualiza as cotações a cada 30 segundos"""
    while True:
        cotacao_service.buscar_cotacoes()
        estado_app["cotacoes"] = cotacao_service.obter_dados()
        estado_app["erro"] = cotacao_service.obter_erro()
        
        # Salvar no banco de dados se não houver erro
        if estado_app["cotacoes"] is not None:
            with app.app_context():
                cotacao_service.salvar_cotacoes_banco()
                
                # ✅ NOVO: Verificar alertas
                alertas = cotacao_service.verificar_alertas()
                estado_app["alertas_disparados"] = alertas
                
                if alertas:
                    print("\n" + "="*60)
                    for alerta in alertas:
                        print(f"🔔 {alerta['mensagem']}")
                    print("="*60 + "\n")
            
            estado_app["total_buscas"] += 1
        
        estado_app["atualizado_em"] = datetime.now().strftime("%H:%M:%S")
        
        time.sleep(30)

# ==================== ROTAS ====================

@app.route('/')
def index():
    """Página principal - Cotações em tempo real"""
    return render_template(
        'index.html',
        pagina='cotacoes',
        cotacoes=estado_app["cotacoes"],
        atualizado_em=estado_app["atualizado_em"],
        total_buscas=estado_app["total_buscas"],
        alertas_disparados=estado_app["alertas_disparados"]  # ✅ NOVO
    )

@app.route('/historico')
def historico():
    """Página de histórico"""
    moeda = request.args.get('moeda', 'USD').upper()
    
    if moeda not in ['USD', 'EUR']:
        moeda = 'USD'
    
    historico_dados = cotacao_service.obter_historico(moeda, 20)
    
    return render_template(
        'index.html',
        pagina='historico',
        moeda=moeda,
        historico=historico_dados,
        atualizado_em=estado_app["atualizado_em"],
        total_buscas=estado_app["total_buscas"],
        alertas_disparados=estado_app["alertas_disparados"]  # ✅ NOVO
    )

@app.route('/alertas')
def alertas():
    """Página de alertas"""
    try:
        alertas_ativos = Alerta.query.filter_by(ativo=True).all()
        alertas_dict = [a.para_dict() for a in alertas_ativos]
    except Exception as e:
        print(f"Erro ao carregar alertas: {e}")
        alertas_dict = []
    
    return render_template(
        'index.html',
        pagina='alertas',
        alertas=alertas_dict,
        atualizado_em=estado_app["atualizado_em"],
        total_buscas=estado_app["total_buscas"],
        alertas_disparados=estado_app["alertas_disparados"]  # ✅ NOVO
    )

@app.route('/criar-alerta', methods=['POST'])
def criar_alerta():
    """Cria um novo alerta"""
    try:
        moeda = request.form.get('moeda', '').upper()
        valor_limite = float(request.form.get('valor_limite', 0))
        tipo = request.form.get('tipo', 'maior').lower()
        
        # Validar dados
        if moeda not in ['USD', 'EUR'] or valor_limite <= 0 or tipo not in ['maior', 'menor']:
            return redirect('/alertas')
        
        # Criar alerta
        alerta = Alerta(
            moeda=moeda,
            valor_limite=valor_limite,
            tipo=tipo
        )
        
        db.session.add(alerta)
        db.session.commit()
        
    except Exception as e:
        print(f"Erro ao criar alerta: {e}")
        db.session.rollback()
    
    return redirect('/alertas')

@app.route('/deletar-alerta/<int:alerta_id>')
def deletar_alerta(alerta_id):
    """Deleta um alerta"""
    try:
        alerta = Alerta.query.get(alerta_id)
        if alerta:
            db.session.delete(alerta)
            db.session.commit()
    except Exception as e:
        print(f"Erro ao deletar alerta: {e}")
        db.session.rollback()
    
    return redirect('/alertas')

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    with app.app_context():
        # Buscar cotações iniciais
        cotacao_service.buscar_cotacoes()
        estado_app["cotacoes"] = cotacao_service.obter_dados()
        estado_app["erro"] = cotacao_service.obter_erro()
        
        # Salvar no banco
        if estado_app["cotacoes"] is not None:
            cotacao_service.salvar_cotacoes_banco()
            estado_app["total_buscas"] = 1
        
        estado_app["atualizado_em"] = datetime.now().strftime("%H:%M:%S")
        
        # Iniciar thread para atualizar periodicamente
        thread_atualizacao = threading.Thread(
            target=atualizar_cotacoes_periodicamente,
            daemon=True
        )
        thread_atualizacao.start()
        
        print("🚀 Servidor iniciando em http://localhost:5000")
        print("📊 Banco de dados: cotacao_hoje.db")
    
    # Iniciar servidor Flask
    app.run(debug=True, port=5000)