import socket
import threading
from password_utils import verificar_password
from db_cliente import crear_tunel, obtener_tunel_por_nombre, guardar_uuid_localmente, get_client_uuid
import requests
import json


class TunnelClient:
    def __init__(self, host, port, tunnel_id, alias, uuid, on_receive_callback):
        self.host = host
        self.port = port
        self.tunnel_id = tunnel_id
        self.alias = alias
        self.uuid = uuid  # ✅ ahora se define desde el inicio
        self.on_receive_callback = on_receive_callback
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False  

    def connect(self):
        self.socket.connect((self.host, self.port))

        from main_refactor import obtener_info_equipo
        info = obtener_info_equipo()

        handshake = {
            "tunnel_id": self.tunnel_id,
            "alias": self.alias,
            "uuid": self.uuid,
            "hostname": info["hostname"],
            "sistema": info["sistema"]
        }

        try:
            requests.post("http://symbolsaps.ddns.net:8000/api/registrar_alias", json={
                "uuid": self.uuid,
                "tunnel_id": self.tunnel_id,
                "alias": self.alias
            })
        except Exception as e:
            print("⚠️ No se pudo registrar alias:", e)

        self.socket.sendall((json.dumps(handshake) + "\n").encode("utf-8"))
        self.running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def receive_loop(self):
        try:
            buffer = ""
            while self.running:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data.decode()

                while "\n" in buffer:
                    mensaje, buffer = buffer.split("\n", 1)
                    self.on_receive_callback(mensaje.strip())
        except Exception as e:
            print(f"Error en receive_loop: {e}")
        finally:
            self.socket.close()
            self.running = False

    def send(self, message):
        try:
            # Si es string JSON, lo convertimos a dict para inspeccionarlo
            if isinstance(message, str):
                msg_dict = json.loads(message)
            else:
                msg_dict = message
                message = json.dumps(message)

            # Para mensajes de texto enviamos exactamente lo que se recibe,
            # sin campos adicionales, pues el servidor espera un formato
            # sencillo y almacena solo el contenido del campo "text".
            if msg_dict.get("type") == "text" and "text" in msg_dict:
                message = json.dumps(msg_dict)

            # Enviar por socket
            self.socket.sendall((message + "\n").encode())


            # El servidor remoto ya registra los mensajes recibidos. Evitamos
            # duplicarlos enviando una petición HTTP adicional.
            # if msg_dict.get("type") == "text" and "text" in msg_dict:
            #     mensaje_texto = {
            #         "tipo": "texto",
            #         "contenido": msg_dict["text"],  # Solo el contenido textual
            #         "tunnel_id": msg_dict["tunnel_id"],
            #         "uuid": msg_dict["uuid"],
            #         "alias": msg_dict["from"]
            #     }
            #     try:
            #         import requests
            #         requests.post("http://symbolsaps.ddns.net:8000/api/messages/save", json=mensaje_texto)
            #     except Exception as e:
            #         print("⚠️ Error registrando mensaje:", e)

        except Exception as e:
            print("❌ Error al enviar mensaje:", e)


    def disconnect(self):
        self.running = False
        self.socket.close()
