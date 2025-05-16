import yfinance as yf
import pandas as pd
from datetime import datetime
from curl_cffi import requests

session = requests.Session(impersonate="chrome")

def data_atual():
    data_atual=datetime.now()
    data_formatada=data_atual.strftime("%Y%m%d")
    return data_formatada

def obter_data_mais_antiga(lista_de_datas):
    """
    Recebe uma lista de strings no formato 'yyyy/mm/dd' e retorna a data mais antiga.
    """
    datas_convertidas = [datetime.strptime(data, "%Y/%m/%d") for data in lista_de_datas]
    data_mais_antiga = min(datas_convertidas)
    return data_mais_antiga.strftime("%Y/%m/%d")

class Carteira:
#Lista de acoes e suas quantidades que o usuario possui.

    def __init__(self):
        self.stocks = {} #dicionario que aponta para o objeto acao
        self.valor_total=0  #somatorio dos valores de cada acao no momento que o usuario abre o app
        self.valorizacao=0  #valorizacao de cada acao esta em percentual. Falta ver como representar isso numa carteira com distribuições desiguais de valor entre ativos
        self.valor_gasto=0  #valor gasto na compra das acoes ate entao. Valorizacao = valor_total - valor_gasto
        self.numero_acoes=0
        self.numero_tickets=0

    def add_stock(self, stock: str, n_stocks: int, data_compra: str = None):
    #antes verifica se ja exsite este stock no dicionario
    #se nao, inicializa classe stock


    #PROBLEMA: devemos fazer com que o cara possa comprar a acao X mais de uma vez e salvar os precos de compra diferentes
    #Deve receber uma data de compra e salvar o valor pago junto com a quantidade de ativos comprados para cada vez que o usuario add ativos na carteira

        if stock in self.stocks:
            # self.stocks[stock].numero_acoes += n_stocks
            # self.stocks[stock].atualiza_valor_gasto(n_stocks, data_compra)
            # self.stocks[stock].atualiza_status_acao()
            self.stocks[stock].add_compra(data_compra,stock, n_stocks)

        else:
            self.stocks[stock] = Stock(stock, n_stocks, data_compra)

    def remove_stock(self, stock: str, n_stocks: int = None):  #remove n acoes de tal ticket
        self.atualiza_status_carteira() #Atualizq o valor atual das acoes para saber o quanto deve descontar do valor atual da carteira
        acoes = self.stocks[stock].numero_acoes

        match n_stocks:
            case None:
                self.valor_total -= self.stocks[stock].valor_atual * self.stocks[stock].numero_acoes
                self.valor_gasto -= self.stocks[stock].valor_gasto
                del self.stocks[stock]

            case _ if n_stocks < acoes:
                #Como determinar o quanto diminuir de valor gasto se o cara pode ter comprado por diferetnes valores?
                #Determinar o valor gasto resultante a partir do lucro e ou prejuizo a partir da cotacao
                self.valor_gasto -= self.stocks[stock].valor_de_compra * n_stocks
                self.valor_total -= self.stocks[stock].valor_atual * n_stocks
                self.stocks[stock].valor_gasto -= self.stocks[stock].valor_de_compra * n_stocks
                self.stocks[stock].numero_acoes -= n_stocks

            case _ if n_stocks == acoes:
                self.valor_total -= self.stocks[stock].valor_atual * self.stocks[stock].numero_acoes
                self.valor_gasto -= self.stocks[stock].valor_gasto
                del self.stocks[stock]
            case _:
                print("Deseja-se deletar mais ações do que se possui na carteira.")

    def limpa_carteira(self):
        self.stocks.clear()

    def gera_relatorio(self):
        # usar stock info pra add % de cada setor etc
        # https://www.geeksforgeeks.org/what-is-yfinance-library/
        self.atualiza_status_carteira()

        print(f"Numero de acoes: {self.numero_acoes}")
        print(f"Numero de tickets: {self.numero_tickets}")
        print(f"Valor gasto: {self.valor_gasto}")
        print(f"Valor total da carteira: {self.valor_total}")
        print(f"Valor gasto: {self.valor_gasto}")
        print(f"Valorizacao da carteira: {self.valorizacao}")


    def atualiza_status_carteira(self):
    # Atualizan valor atual e valor gasto da carteira
        for stock in self.stocks.values():
            stock.atualiza_status_acao()

        self.valor_total = sum(stock.valor_atual for stock in self.stocks.values())
        self.valor_gasto = sum(stock.valor_gasto for stock in self.stocks.values())
        self.numero_tickets = len(self.stocks)
        self.numero_acoes = sum(stock.numero_acoes for stock in self.stocks.values())

        #Valorização = ((valor_atual - valor_gasto) / valor_gasto) * 100
        self.valorizacao = ((self.valor_total - self.valor_gasto) / self.valor_gasto ) * 100    #Em porcentagem

class Compra:
#Classe para armazenar os dados de cada compra do usuario, contendo numero de ativos, data de compra e preco de compra
    def __init__(self, data_compra: str, valor_de_compra: int, numero_de_ativos: int):
        self.data_de_compra=data_compra
        self.valor_de_compra=valor_de_compra
        self.ativos_comprados=numero_de_ativos


class Stock:
    def __init__(self, ticket: str, n_stocks: int, data_compra: str = None):
    #OBS: data compra no formato yyyy/mm/dd
        self.numero_acoes=n_stocks
        self.ticket=ticket
        if data_compra is None:
            data_compra = data_atual()

        acao = yf.Ticker(ticket, session=session)
        acao_historico = acao.history(start=data_compra)    #usa formato de data YYYY/mm/dd

        # Verifica se a data existe. Nao existe para final de semana ou feriado. No entanto, se o outro parametro 
        # existir, nao retorna vazio pois pega ele

        if acao_historico.empty:
            raise ValueError(f"Sem dados para a data de compra: {data_compra}")

        self.maxima_historica=acao_historico["High"].max()
        self.minima_historica=acao_historico["Low"].min()
        self.setor=acao.info['sector']

        #Dicionario onde a chave é o a data da acao e o valor um objeto Compra
        self.compras = {}
        valor_compra = acao_historico["Open"].iloc[0]
        compra = Compra(data_compra, valor_compra, n_stocks)
        self.compras[data_compra] = compra

        self.valor_gasto = self.compras[data_compra].valor_de_compra * self.compras[data_compra].ativos_comprados
        self.valor_atual = 0    #valor atual total do ativo sera averiguado somente quando quisermos obter valorização, nao tem pra que guardar ele ja agora
        self.valorizacao = 0


    def add_compra(self, data_compra, ticket, n_stocks):
        if data_compra == None:
            data_compra = data_atual() 
        # adiciona objeto Compra para o dicionario e já atualiza valor_gasto
        self.numero_acoes += n_stocks
        acao = yf.Ticker(ticket, session=session)
        acao_historico = acao.history(start=data_compra)
        if acao_historico.empty:
            raise ValueError(f"Sem dados para a data de compra: {data_compra}")
        valor_compra = acao_historico["Open"].iloc[0]
        compra = Compra(data_compra, valor_compra, n_stocks)
        self.compras[data_compra] = compra

        self.valor_gasto += self.compras[data_compra].valor_de_compra * self.compras[data_compra].ativos_comprados     


    def atualiza_status_acao(self):
    # atualiza o valor atual, maximo e minimo
        acao=yf.Ticker(self.ticket, session=session)
        data_primeira_compra = obter_data_mais_antiga(list(self.compras.keys()))

        acao_historico = acao.history(start=self.data_primeira_compra)
        self.maxima_historica=acao_historico["High"].max()
        self.minima_historica=acao_historico["Low"].min()
        self.valor_atual = acao_historico["Open"].iloc[-1]
        #modificar a valorizacao para depender apenas de valor gasto, ja que pode ter comprado a acao por precos diferentes
        valor_atual_total = self.valor_atual * self.numero_acoes
        self.valorizacao = ((valor_atual_total - self.valor_gasto) / self.valor_gasto) * 100 #Em porcentagem
        

ticket = "AAPL"
carteira = Carteira()
carteira.add_stock(ticket, 1, "2025-05-12")
carteira.add_stock("GOOG", 2, "2025-05-12")
carteira.remove_stock("GOOG", 1)
carteira.gera_relatorio()
