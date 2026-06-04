from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import os
import threading
import random
import time
import pickle
from requests import get
import constMP as Config
from cards import valores

class PeerCommunicator:
    def __init__(self):
        self.info = None

        self.game_state = None
        self.placar = None

        self.peer_id = None
        self.num_messages = 0
        self.peers = []

        self.send_socket = socket(AF_INET, SOCK_DGRAM)
        self.recv_socket = socket(AF_INET, SOCK_DGRAM)
        self.recv_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.recv_socket.bind(('0.0.0.0', Config.PEER_UDP_PORT))

        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', Config.PEER_TCP_PORT))
        self.server_socket.listen(1)

    def new_game_state(self):
        self.game_state = {
            "fase": "PLAYING",
            "id_mao": 1,
            "turno": 0,
            "vaza": 1,
            "tentos": 1,
            "current_player": 0,
            "cartas_mesa": [],
            "vazas_ganhas": {"A": 0, "B": 0},
            "valor_mao": 1,
            "last_request_player": None
        }

    def get_public_ip(self):
        return get('https://api.ipify.org').content.decode('utf8')

    def register_with_group_manager(self):
        response = self.send_request({
            "op": "register", 
            "ipaddr": self.get_public_ip(), 
            "port": Config.PEER_UDP_PORT
        })
        if response.get("status") == 'error':
            print(response.get("message"))
            exit(0)

        self.peer_id = response["player_id"]
        print(f"Registrado como jogador {self.peer_id}")

    def get_table_info(self):
        response = self.send_request({"op": "table"})
        return response

    def get_cards(self):
        response = self.send_request({
            "op": "hand", "player_id": self.peer_id
        })
        return response["cards"]

    def get_list_of_peers(self):
        self.peers = self.send_request({"op": "list"})
        # remove self IP if present
        my_ip = self.get_public_ip()
        self.peers = [p for p in self.peers if p != my_ip]
        return self.peers

    def wait_to_start(self):
        conn, _ = self.server_socket.accept()
        msg_pack = conn.recv(1024)
        self.peer_id, self.num_messages = pickle.loads(msg_pack)
        conn.send(pickle.dumps(f"Processo peer {self.peer_id} iniciado."))
        conn.close()
        return self.peer_id, self.num_messages

    def send_handshakes(self):
        for addr in self.peers:
            msg_pack = pickle.dumps(('READY', self.peer_id))
            self.send_socket.sendto(msg_pack, (addr, Config.PEER_UDP_PORT))

    def send_messages(self):
        for msg_number in range(self.num_messages):
            time.sleep(random.uniform(0.01, 0.1))
            msg_pack = pickle.dumps((self.peer_id, msg_number))
            for addr in self.peers:
                self.send_socket.sendto(msg_pack, (addr, Config.PEER_UDP_PORT))

    def send_stop_signal(self):
        msg_pack = pickle.dumps((-1, -1))
        for addr in self.peers:
            self.send_socket.sendto(msg_pack, (addr, Config.PEER_UDP_PORT))

    def getParceiro(self, teams):
        me = self.peer_id
        for team_name, players in teams.items():
            if me in players:
                my_team = team_name
                parceiro = players[0] if players[1] == me else players[1]

        self.parceiro = parceiro
        return {
            "team": my_team,
            "parceiro": parceiro
        }

    def avancar_turno(self):
        order = self.info["order"]
        current_index = order.index(self.game_state["current_player"])
        next_index = (current_index + 1) % 4
        self.game_state["current_player"] = order[next_index]
        self.game_state["turno"] += 1

    def multicast_msg(self, msg):
        msg_pack = pickle.dumps(msg)
        for addr in self.peers:
            self.send_socket.sendto(msg_pack, (addr, Config.PEER_UDP_PORT))

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def mostrar_mesa(self, cards):
        self.clear_screen()
        print(f"Jogador {self.peer_id} | Time {self.info['team']} | Parceiro {self.info['parceiro']}")
        print(f"Vaza {self.game_state['vaza']} | Turno {self.game_state['turno']} | Vez do jogador {self.game_state['current_player']}")
        print(f"Vazas ganhas: {self.game_state['vazas_ganhas']}")
        if self.placar: print(f"Placar: A-{self.placar['A']} x B-{self.placar['B']}") 
        else: print(f"Placar: A-0 x B-0")
        print()
        print("Cartas na mesa:")
        if self.game_state["cartas_mesa"]:
            for play in self.game_state["cartas_mesa"]:
                print(f"  Jogador {play['player_id']}: {play['card']}")
        else:
            print("  Nenhuma carta jogada ainda.")
        print()
        print("Suas cartas:")
        for index, carta in enumerate(cards):
            print(f"  {index}: {carta}")
        print()

    def prompt_jogada(self, cards):
        self.mostrar_mesa(cards)
        msg = {
            # "type": "", # play, truco_accept, truco, seis, doze
            "vaza": self.game_state["vaza"],
            "turno": self.game_state["turno"],
            "valor_mao": self.game_state["valor_mao"],
            "player_id": self.peer_id,
            "card": None
        }

        fase = self.game_state["fase"]

        if fase == "PLAYING":    # Jogo normal (sem estar em pedido de truco/6/12)
            if self.game_state["valor_mao"] == 1:
                print("E sua vez, jogue uma carta ou peca truco...")
                print("correr: 9 | pedir truco: 8")
                inp = input("Digite sua jogada: ")
                if inp == '9':
                    msg["type"] = "correr"
                elif inp == '8':
                    msg["type"] = "truco"
                else:
                    msg["card"] = cards[int(inp)]
                    msg["type"] = "play"
                    cards.remove(cards[int(inp)])
            elif self.game_state["valor_mao"] == 3:                          # Jogo trucado
                print("(3) E sua vez, jogue uma carta ou peca seis...")
                print("correr: 9 | pedir seis: 8")
                inp = input("Digite sua jogada: ")
                if inp == '9':
                    msg["type"] = "correr"
                elif inp == '8':
                    msg["type"] = "seis"
                else:
                    msg["card"] = cards[int(inp)]
                    msg["type"] = "play"
                    cards.remove(cards[int(inp)])
            elif self.game_state["valor_mao"] == 6:                          # Alguem pediu 6
                print("(6) E sua vez, jogue uma carta ou peca doze...")
                print("correr: 9 | pedir doze: 8")
                inp = input("Digite sua jogada: ")
                if inp == '9':
                    msg["type"] = "correr"
                elif inp == '8':
                    msg["type"] = "doze"
                else:
                    msg["card"] = cards[int(inp)]
                    msg["type"] = "play"
                    cards.remove(cards[int(inp)])
            elif self.game_state["valor_mao"] == 12:                          # Alguem pediu 12
                print("(12) E sua vez, jogue uma carta ou corra...")
                print("correr: 9")
                inp = input("Digite sua jogada: ")
                if inp == '9':
                    msg["type"] = "correr"
                else:
                    msg["card"] = cards[int(inp)]
                    msg["type"] = "play"
                    cards.remove(cards[int(inp)])
        elif fase == "MUST_PLAY":
            print("Pedido aceito, jogue uma carta...")
            inp = input("Digite sua jogada: ")
            msg["card"] = cards[int(inp)]
            msg["type"] = "must_play"
            cards.remove(cards[int(inp)])

        elif fase == "TRUCO":    # Voce recebeu um pedido de truco
            print("E sua vez, aceite o truco, peca 6 ou corra")
            print("correr: 9 | aceitar truco: 8 | pedir seis: 7")
            inp = input("Digite sua jogada: ")
            if inp == '9':
                msg["type"] = "correr"
            elif inp == '8':
                msg["type"] = "accept"
                msg["valor_mao"] = 3
            elif inp == '7':
                msg["type"] = "seis"

        elif fase == "SEIS":    # Voce recebeu um pedido de seis
            print("E sua vez, aceite o seis, peca doze ou corra")
            print("correr: 9 | aceitar seis: 8 | pedir doze: 7")
            inp = input("Digite sua jogada: ")
            if inp == '9':
                msg["type"] = "correr"
            elif inp == '8':
                msg["type"] = "accept"
                msg["valor_mao"] = 6
            elif inp == '7':
                msg["type"] = "doze"

        elif fase == "DOZE":    # Voce recebeu um pedido de doze
            print("E sua vez, aceite o doze, peca 6 ou corra")
            print("correr: 9 | aceitar doze: 8")
            inp = input("Digite sua jogada: ")
            if inp == '9':
                msg["type"] = "correr"
            elif inp == '8':
                msg["type"] = "accept"
                msg["valor_mao"] = 12

        return msg
    
    def get_team_of_player(self, player_id):
        for team, players in self.info["teams"].items():
            if player_id in players:
                return team

    def check_vaza_winner(self):
        winning_play = self.game_state["cartas_mesa"][0]

        for play in self.game_state["cartas_mesa"][1:]:
            if valores[play["card"]] > valores[winning_play["card"]]:
                winning_play = play

        winner_player = winning_play["player_id"]
        winner_team = self.get_team_of_player(winner_player)

        return winner_player, winner_team

    def is_my_turn(self):
        return self.game_state["current_player"] == self.peer_id

    def send_result(self, winner):
        return self.send_request({"op": "register_win", "player_id": self.peer_id, "winner_team": winner, "valor_mao": self.game_state["valor_mao"]})
    
    def send_request(self, request):
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((Config.GROUPMNGR_ADDR, Config.GROUPMNGR_TCP_PORT))
        client_socket.send(pickle.dumps(request))
        response = pickle.loads(client_socket.recv(2048))
        client_socket.close()
        return response

    def check_gameover(self):
        if not self.placar: 
            return False
        elif self.placar['A'] >= 12 or self.placar['B'] >= 12:
            return True
        return False

    def proximo_jogador(self, player_id):
        order = self.info["order"]
        index = order.index(player_id)
        return order[(index + 1) % 4]
        
    def jogador_anterior(self, player_id):
        order = self.info["order"]
        index = order.index(player_id)
        return order[(index - 1) % 4]

    def registrar_pedido_truco(self, msg):
        previous_requester = self.game_state["last_request_player"]
        self.game_state["last_request_player"] = msg["player_id"]
        self.game_state["fase"] = msg["type"].upper()

        if previous_requester is None:
            self.game_state["current_player"] = self.proximo_jogador(msg["player_id"])
        else:
            self.game_state["current_player"] = previous_requester

    def run(self):
        self.register_with_group_manager()
        while True:
            # Espera ate 4 jogadores entrarem
            while True:
                response = self.get_table_info()
                if response.get("status") == 'ok':
                    self.get_list_of_peers()
                    self.info = self.getParceiro(response.get("teams"))
                    self.info["order"] = response.get("order")
                    # cicla uma vez pra baixo pras outras vezes cliclarem e ignorar a primeira mao
                    self.info["order"] = self.info["order"][-1:] + self.info["order"][:-1] 
                    self.info["teams"] = response.get("teams")
                    print(f"Jogadores conectados, seu time: {self.info['team']}")
                    print(f"Você é o jogador {self.peer_id}, sua dupla é o jogador: {self.info['parceiro']}")
                    print(f"Ordem da mesa: {self.info['order']}")
                    break
                else:
                    print("Aguardando jogadores...")
                    time.sleep(2)
            
            # Logica do jogo principal
            self.new_game_state()
            self.info["order"] = self.info["order"][1:] + self.info["order"][:1]
            order = self.info["order"]
            self.game_state["current_player"] = order[0]

            cards = self.get_cards()
            
            self.mostrar_mesa(cards)

            while self.game_state["fase"] != "HAND_FINISHED":   
                winner_player = None
                winner_team = None
                while self.game_state["fase"] != "HAND_FINISHED" and len(self.game_state["cartas_mesa"]) < 4:  # enquanto nao tiverem jogado 4 cartas
                    # ----------- SE FOR MINHA VEZ
                    if self.is_my_turn():                      
                        msg = self.prompt_jogada(cards)
                        tipo_msg = msg.get("type")
                        self.multicast_msg(msg)                     # mando a minha jogada pros peers
                        if(tipo_msg == "play"): 
                            self.game_state["cartas_mesa"].append({"card": msg["card"], "player_id": msg["player_id"]})  # adiciono minha propria jogada na minha mesa
                            self.avancar_turno()
                            self.mostrar_mesa(cards)
                        elif(tipo_msg == "must_play"):              # descendo qnd aceitam meu truco
                            self.game_state["cartas_mesa"].append({"card": msg["card"], "player_id": msg["player_id"]}) 
                            self.game_state["fase"] = "PLAYING"
                            self.avancar_turno()
                            self.mostrar_mesa(cards)
                        elif tipo_msg in ["truco", "seis", "doze"]:
                            self.registrar_pedido_truco(msg)
                        elif(tipo_msg == "accept"):
                            self.game_state["valor_mao"] = msg.get("valor_mao")
                            self.game_state["fase"] = "MUST_PLAY"
                            self.game_state["current_player"] = self.game_state["last_request_player"]
                            self.game_state["last_request_player"] = None
                        elif(tipo_msg == "correr"):
                            self.game_state["fase"] = "HAND_FINISHED"
                            runner_team = self.get_team_of_player(msg["player_id"])
                            winner_team = "A" if runner_team == "B" else "B"
                            winner_player = self.jogador_anterior(msg["player_id"])
                    
                    # ----------- SE NAO FOR MINHA VEZ
                    else:                                      
                        msg_pack = self.recv_socket.recv(1024)  # recebe a jogada de quem for
                        msg = pickle.loads(msg_pack)
                        tipo_msg = msg.get("type")
                        if tipo_msg == "play":
                            print(f"Jogador {msg.get('player_id')} esta jogando...")
                            self.game_state["cartas_mesa"].append(msg)   # coloca a jogada na minha mesa local
                            self.avancar_turno()
                            self.mostrar_mesa(cards)
                        elif tipo_msg == "must_play": 
                            print(f"Jogador {msg.get('player_id')} tem que descer...")
                            self.game_state["cartas_mesa"].append(msg)   # coloca a jogada na minha mesa local
                            self.game_state["fase"] = "PLAYING"
                            self.avancar_turno()
                            self.mostrar_mesa(cards)
                        elif tipo_msg in ["truco", "seis", "doze"]:    # Jogo vai para estado de "pedido de truco/6/12"
                            print(f"Jogador {msg.get('player_id')} pediu {tipo_msg}...")
                            self.registrar_pedido_truco(msg)
                        elif tipo_msg == "accept":                                  # Aceitou o pedido de truco/6/12
                            print(f"Jogador {msg.get('player_id')} aceitou o pedido de {self.game_state['fase'].lower()}...")
                            self.game_state["valor_mao"] = msg.get("valor_mao")     # Jogo comeca a valer N tentos
                            self.game_state["fase"] = "MUST_PLAY"                     # volta ao estado de jogo normal
                            self.game_state["current_player"] = self.game_state["last_request_player"]
                            self.game_state["last_request_player"] = None
                        elif(tipo_msg == "correr"):
                            print(f"Jogador {msg.get('player_id')} correu...")
                            self.game_state["fase"] = "HAND_FINISHED"
                            runner_team = self.get_team_of_player(msg["player_id"])
                            winner_team = "A" if runner_team == "B" else "B"
                            winner_player = self.jogador_anterior(msg["player_id"])


                if(not winner_team and not winner_player):
                    winner_player, winner_team = self.check_vaza_winner()    # checa quem ganhou a mao
                    self.game_state["vazas_ganhas"][winner_team] += 1
                    self.mostrar_mesa(cards)

                print(f"Vaza {self.game_state['vaza']} vencida pelo jogador {winner_player} - time {winner_team}")
                time.sleep(2)

                if self.game_state["vazas_ganhas"][winner_team] == 2 or self.game_state["fase"] == "HAND_FINISHED":    # ve se o ganhador fez 2 vazas ja
                    self.game_state["fase"] = "HAND_FINISHED"
                    self.mostrar_mesa(cards)
                    print(f"Mao finalizada. Time vencedor: {winner_team}")
                    if self.peer_id == 0:              # So o peer 0 envia, pra nao somar o placar + vzs
                        self.send_result(winner_team)
                    else: 
                        time.sleep(2)           # tempo para atualizar o placar
                    req = self.send_request({"op": "placar"})
                    self.placar = req['placar']
                    print(f"Placar: {self.placar}")
                    game_over = self.check_gameover()
                    if game_over:
                        print("Jogo encerrado! Saindo...")
                        time.sleep(5)
                        return
                else:
                    self.game_state["vaza"] += 1
                    self.game_state["cartas_mesa"] = []
                    self.game_state["current_player"] = winner_player
                    self.mostrar_mesa(cards)


if __name__ == "__main__":
    PeerCommunicator().run()
