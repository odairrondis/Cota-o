import requests
from models import Cotacao, Alerta
from database import db
from datetime import datetime

class CotacaoService:
    """Serviço para obter cotações de moedas e gerenciar banco de dados"""
    
    def __init__(self):
        self.url_api = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL"
        self.erro = None
        self.dados = None
        self.alertas_disparados = []  # ✅ NOVO: lista de alertas disparados
    
    def buscar_cotacoes(self):
        """
        Busca as cotações atuais da API
        Retorna um dicionário com os dados ou None se houver erro
        """
        try:
            resposta = requests.get(self.url_api, timeout=5)
            resposta.raise_for_status()
            
            dados_brutos = resposta.json()
            
            # Processar dados
            self.dados = {
                "usd": {
                    "moeda": "USD",
                    "nome": "Dólar Americano",
                    "valor_atual": float(dados_brutos['USDBRL']['bid']),
                    "variacao": float(dados_brutos['USDBRL']['pctChange']),
                    "timestamp": dados_brutos['USDBRL']['create_date']
                },
                "eur": {
                    "moeda": "EUR",
                    "nome": "Euro",
                    "valor_atual": float(dados_brutos['EURBRL']['bid']),
                    "variacao": float(dados_brutos['EURBRL']['pctChange']),
                    "timestamp": dados_brutos['EURBRL']['create_date']
                }
            }
            
            self.erro = None
            return self.dados
            
        except requests.exceptions.Timeout:
            self.erro = "Erro: Requisição expirou. Tente novamente."
            return None
        except requests.exceptions.ConnectionError:
            self.erro = "Erro: Sem conexão com a internet."
            return None
        except requests.exceptions.HTTPError as e:
            self.erro = f"Erro HTTP: {e.response.status_code}"
            return None
        except (KeyError, ValueError):
            self.erro = "Erro: Formato de dados inválido da API."
            return None
        except Exception as e:
            self.erro = f"Erro desconhecido: {str(e)}"
            return None
    
    def salvar_cotacoes_banco(self):
        """Salva as cotações atuais no banco de dados"""
        if self.dados is None:
            return False
        
        try:
            # Salvar USD
            cotacao_usd = Cotacao(
                moeda='USD',
                nome_moeda='Dólar Americano',
                valor_atual=self.dados['usd']['valor_atual'],
                variacao=self.dados['usd']['variacao'],
                timestamp_api=self.dados['usd']['timestamp']
            )
            
            # Salvar EUR
            cotacao_eur = Cotacao(
                moeda='EUR',
                nome_moeda='Euro',
                valor_atual=self.dados['eur']['valor_atual'],
                variacao=self.dados['eur']['variacao'],
                timestamp_api=self.dados['eur']['timestamp']
            )
            
            db.session.add(cotacao_usd)
            db.session.add(cotacao_eur)
            db.session.commit()
            
            return True
        except Exception as e:
            print(f"Erro ao salvar cotações no banco: {e}")
            db.session.rollback()
            return False
    
    def verificar_alertas(self):
        """
        ✅ NOVO: Verifica se algum alerta deve ser disparado
        Retorna uma lista com os alertas disparados
        """
        self.alertas_disparados = []
        
        if self.dados is None:
            return []
        
        try:
            # Buscar todos os alertas ativos e não disparados
            alertas = Alerta.query.filter_by(ativo=True, disparado=False).all()
            
            for alerta in alertas:
                valor_cotacao = None
                
                # Obter o valor da cotação atual
                if alerta.moeda == 'USD':
                    valor_cotacao = self.dados['usd']['valor_atual']
                elif alerta.moeda == 'EUR':
                    valor_cotacao = self.dados['eur']['valor_atual']
                
                if valor_cotacao is None:
                    continue
                
                # Verificar se o alerta foi acionado
                alerta_disparado = False
                
                if alerta.tipo == 'maior' and valor_cotacao >= alerta.valor_limite:
                    alerta_disparado = True
                elif alerta.tipo == 'menor' and valor_cotacao <= alerta.valor_limite:
                    alerta_disparado = True
                
                # Se disparado, marcar no banco de dados
                if alerta_disparado:
                    alerta.disparado = True
                    alerta.disparado_em = datetime.now()
                    db.session.commit()
                    
                    # Adicionar à lista de alertas disparados
                    mensagem = f"🔔 ALERTA: {alerta.moeda} {alerta.tipo.upper()} R$ {alerta.valor_limite:.2f} - Valor atual: R$ {valor_cotacao:.2f}"
                    self.alertas_disparados.append({
                        'id': alerta.id,
                        'moeda': alerta.moeda,
                        'tipo': alerta.tipo,
                        'valor_limite': alerta.valor_limite,
                        'valor_atual': valor_cotacao,
                        'mensagem': mensagem
                    })
            
            return self.alertas_disparados
            
        except Exception as e:
            print(f"Erro ao verificar alertas: {e}")
            return []
    
    def obter_alertas_disparados(self):
        """✅ NOVO: Retorna os alertas disparados na última verificação"""
        return self.alertas_disparados
    
    def obter_historico(self, moeda='USD', limite=10):
        """Retorna o histórico de cotações do banco de dados"""
        try:
            cotacoes = Cotacao.query.filter_by(moeda=moeda)\
                                    .order_by(Cotacao.criado_em.desc())\
                                    .limit(limite)\
                                    .all()
            
            return [c.para_dict() for c in cotacoes]
        except Exception as e:
            print(f"Erro ao buscar histórico: {e}")
            return []
    
    def obter_dados(self):
        """Retorna os dados das cotações"""
        return self.dados
    
    def obter_erro(self):
        """Retorna a mensagem de erro, se houver"""
        return self.erro