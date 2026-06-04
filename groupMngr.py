from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import pickle
import constMP as Config
from cards import cartas, valores
import random

class GroupManager:
    table_order = None
    teams = None
    cartas_disponiveis = set(cartas)

    def reset_cartas(self):
        self.cartas_disponiveis = set(cartas)

    def __init__(self, port=None):
        self.port = port or Config.GROUPMNGR_TCP_PORT
        self.membership = []
        self.server_socket = None

    def start(self):
        """Inicia o loop principal do servidor."""
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(6)
        self.placar = {
            "A": 0,
            "B": 0
        }

        print(f"GroupManager escutando na porta {self.port}...")

        try:
            while True:
                (conn, addr) = self.server_socket.accept()
                msg = conn.recv(2048)
                req = pickle.loads(msg)
                if self.should_stop(req, conn):
                    break
                self.receber_request(conn, req)
        finally:
            if self.server_socket:
                self.server_socket.close()

    def should_stop(self, req, conn):
        if req.get("op") == "stop":
            print("Parando o GroupManager.")
            conn.close()
            return True
        else:
            return False
        
    def escolher_cartas(self):
        self.reset_cartas()
        hands = {}

        for player_id in range(4):
            chosen = random.sample(list(self.cartas_disponiveis), 3)
            hands[player_id] = chosen
            for c in chosen:
                self.cartas_disponiveis.remove(c)
        return hands

    def receber_request(self, conn, req):
        operation = req.get("op")

        if operation == 'register':
            if len(self.membership) >= 4:
                conn.send(pickle.dumps({"status": "error", "message": "mesa cheia"}))
            else: 
                conn.send(pickle.dumps({"status": "ok", "player_id": len(self.membership)}))
                self._register(req)
                if len(self.membership) == 4:
                    self.cartas = self.escolher_cartas()
                    self.table_order = [0, 1, 2, 3]
                    self.teams = {
                        "A": [0, 2], 
                        "B": [1, 3]
                    }
                    print("Mesa formada")
        elif operation == "table":
            if(self.table_order and self.teams):
                conn.send(pickle.dumps({
                        "status": "ok", 
                        "order": self.table_order,
                        "teams": self.teams,
                    }))
            else:
                conn.send(pickle.dumps({
                    "status": "aguardando", 
                    "message": "Aguardando jogadores"
                }))
        elif operation == "hand":            # atualiza o placar e envia a proxima mao
            player_id = req.get("player_id")
            conn.send(pickle.dumps({
                "status": "ok", 
                "cards": self.cartas[player_id]
            }))
        elif operation == "register_win":            # atualiza o placar 
            ganhador = req.get("winner_team")
            player_id = req.get("player_id")
            valor_mao = req.get("valor_mao")
            self.placar[ganhador] += int(valor_mao)
            print(f"Placar: {self.placar}")
            conn.send(pickle.dumps({
                "status": "ok", 
            }))
            if(self.placar["A"] >= 12 or self.placar["B"] >= 12):
                return
        elif operation == "placar":
            conn.send(pickle.dumps({
                "status": "ok", 
                "placar": self.placar
            }))
        elif operation == "list":
            self._list_peers(conn)
        elif operation == "unregister":
            self._unregister(req)
        else:       
            print(f"Operação desconhecida: {operation}")

        conn.close()
        
    # def checar_mesa(conn, addr):
    #     if operation == 'register':
    #         print("")

    def _register(self, req):
        """
        Registra um novo peer na lista de membros.

        Args:
            req: Dicionário com "ipaddr" e "port" do peer.
        """
        peer_info = (req["ipaddr"], req["port"])
        self.membership.append(peer_info)
        print(f"Peer registrado: {req}")

    def _list_peers(self, conn):
        """
        Envia a lista de endereços IP dos peers registrados.

        Args:
            conn: Conexão TCP para enviar a resposta.
        """
        peer_ips = [member[0] for member in self.membership]
        print(f"Lista de peers enviada: {peer_ips}")
        conn.send(pickle.dumps(peer_ips))

    def _unregister(self, req):
        """
        Remove um peer da lista de membros.

        Args:
            req: Dicionário com "ipaddr" e "port" do peer a remover.
        """
        peer_info = (req.get("ipaddr"), req.get("port"))
        if peer_info in self.membership:
            self.membership.remove(peer_info)
            print(f"Peer desregistrado: {req}")
        else:
            print(f"Peer não encontrado para desregistro: {req}")


# Ponto de entrada
if __name__ == "__main__":
    manager = GroupManager()
    manager.start()
