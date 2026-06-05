import os
from socket import AF_INET, SOCK_DGRAM, socket

import zmq
from requests import get

import constMP as Config


def get_advertised_host(env_var="PROCESS_HOST"):
    configured_host = os.environ.get(env_var)
    if configured_host:
        return configured_host

    try:
        return get("https://api.ipify.org", timeout=2).content.decode("utf8")
    except Exception:
        pass

    try:
        probe = socket(AF_INET, SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        host = probe.getsockname()[0]
        probe.close()
        return host
    except Exception:
        return "127.0.0.1"


class NamingClient:
    def __init__(self, host=None, port=None, timeout_ms=5000):
        self.host = host or Config.NAMING_SERVICE_ADDR
        self.port = port or Config.NAMING_SERVICE_PORT
        self.timeout_ms = timeout_ms
        self.context = zmq.Context.instance()

    def _request(self, payload):
        socket = self.context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
        socket.connect(f"tcp://{self.host}:{self.port}")

        try:
            socket.send_json(payload)
            return socket.recv_json()
        except zmq.Again:
            return {
                "status": "error",
                "message": "timeout ao acessar o servico de nomes",
            }
        finally:
            socket.close()

    def bind(self, name, address):
        return self._request({
            "op": "bind",
            "name": name,
            "address": address,
        })

    def lookup(self, name):
        return self._request({
            "op": "lookup",
            "name": name,
        })

    def unbind(self, name):
        return self._request({
            "op": "unbind",
            "name": name,
        })

    def register(self, name, process_type):
        return self._request({
            "op": "register",
            "name": name,
            "type": process_type,
        })

    def discover(self, process_type):
        return self._request({
            "op": "discover",
            "type": process_type,
        })

    def rebind(self, name, address, process_type=None):
        response = self.bind(name, address)
        if response.get("status") == "error" and "ja registrado" in response.get("message", ""):
            self.unbind(name)
            response = self.bind(name, address)

        if response.get("status") != "ok":
            return response

        if process_type:
            return self.register(name, process_type)

        return response
