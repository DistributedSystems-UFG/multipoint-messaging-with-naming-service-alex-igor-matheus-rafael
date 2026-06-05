import zmq

import constMP as Config


class NamingService:
    def __init__(self, host=None, port=None):
        self.host = host or Config.NAMING_SERVICE_ADDR
        self.port = port or Config.NAMING_SERVICE_PORT
        self.records = {}
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)

    def start(self):
        endpoint = f"tcp://*:{self.port}"
        self.socket.bind(endpoint)
        print(f"NamingService escutando em {endpoint}...")

        try:
            while True:
                req = self.socket.recv_json()
                if req.get("op") == "stop":
                    self.socket.send_json({"status": "ok"})
                    break

                response = self.handle_request(req)
                self.socket.send_json(response)
        finally:
            self.socket.close()
            self.context.term()

    def handle_request(self, req):
        operation = req.get("op")

        if operation == "bind":
            return self.bind(req.get("name"), req.get("address"))
        if operation == "lookup":
            return self.lookup(req.get("name"))
        if operation == "unbind":
            return self.unbind(req.get("name"))
        if operation == "register":
            return self.register(req.get("name"), req.get("type"))
        if operation == "discover":
            return self.discover(req.get("type"))

        return {"status": "error", "message": f"operacao desconhecida: {operation}"}

    def bind(self, name, address):
        if not name or not address:
            return {"status": "error", "message": "nome e endereco sao obrigatorios"}
        if name in self.records:
            return {"status": "error", "message": "nome ja registrado"}

        self.records[name] = {
            "address": address,
            "type": None,
        }
        print(f"bind: {name} -> {address}")
        return {"status": "ok"}

    def lookup(self, name):
        record = self.records.get(name)
        if not record:
            return {"status": "error", "message": "nome nao encontrado"}

        return {
            "status": "ok",
            "name": name,
            "address": record["address"],
            "type": record["type"],
        }

    def unbind(self, name):
        if name not in self.records:
            return {"status": "error", "message": "nome nao encontrado"}

        del self.records[name]
        print(f"unbind: {name}")
        return {"status": "ok"}

    def register(self, name, process_type):
        if name not in self.records:
            return {"status": "error", "message": "nome nao encontrado"}
        if not process_type:
            return {"status": "error", "message": "tipo e obrigatorio"}

        self.records[name]["type"] = process_type
        print(f"register: {name} como {process_type}")
        return {"status": "ok"}

    def discover(self, process_type):
        if not process_type:
            return {"status": "error", "message": "tipo e obrigatorio"}

        records = [
            {"name": name, "address": record["address"]}
            for name, record in self.records.items()
            if record["type"] == process_type
        ]
        return {"status": "ok", "records": records}


if __name__ == "__main__":
    NamingService().start()
