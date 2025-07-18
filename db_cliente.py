try:
    import mysql.connector
except Exception as e:  # pragma: no cover - env may lack MySQL
    mysql = None
    from app_logger import logger
    logger.warning(f"No se pudo importar mysql.connector: {e}")
import os
try:
    import requests
except Exception as e:  # pragma: no cover - env may lack requests
    requests = None
    from app_logger import logger
    logger.warning(f"No se pudo importar requests: {e}")
import uuid
import socket
import platform

def get_connection():
    if mysql is None:
        raise RuntimeError("mysql.connector no disponible")
    return mysql.connector.connect(
        host='symbolsaps.ddns.net',
        user='admin',
        password='Febrero2025*-+',
        database='securex',
        connection_timeout=5
    )

def crear_tunel(nombre, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tunnels (name, password_hash) VALUES (%s, %s)",
        (nombre, password_hash)
    )
    conn.commit()
    tunnel_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return tunnel_id

def obtener_tunel_por_nombre(nombre):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tunnels WHERE name = %s", (nombre,))
    tunel = cursor.fetchone()
    cursor.close()
    conn.close()
    return tunel

def guardar_uuid_localmente(uuid_value):
    path = os.path.expanduser("~/.betty")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, ".uuid"), "w") as f:
        f.write(uuid_value)

def get_client_uuid():
    path = os.path.expanduser("~/.betty/.uuid")
    if not os.path.exists(path):
        new_uuid = str(uuid.uuid4())
        guardar_uuid_localmente(new_uuid)
        from app_logger import logger
        logger.info(f"UUID generado: {new_uuid}")
        return new_uuid
    else:
        with open(path, "r") as f:
            return f.read().strip()

def registrar_cliente(uuid_value, hostname, sistema):
    if not requests:
        from app_logger import logger
        logger.warning("requests no disponible; no se enviará al backend")
        return
    try:
        response = requests.post(
            "http://symbolsaps.ddns.net:8000/api/registrar_cliente",
            json={
                "uuid": uuid_value,
                "hostname": hostname,
                "sistema": sistema
            },
            timeout=5
        )
        response.raise_for_status()
        from app_logger import logger
        logger.info("Cliente registrado correctamente en el backend.")
    except Exception as e:
        from app_logger import logger
        logger.error(f"Error al registrar cliente en el backend: {e}")

def registrar_alias_cliente(uuid_value, tunnel_id, alias):
    payload = {
        "uuid": uuid_value,
        "tunnel_id": tunnel_id,
        "alias": alias
    }
    if not requests:
        from app_logger import logger
        logger.warning("requests no disponible; no se enviará alias al backend")
        return
    try:
        response = requests.post(
            "http://symbolsaps.ddns.net:8000/api/registrar_alias",
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        from app_logger import logger
        logger.info("Alias registrado correctamente")
    except Exception as e:
        from app_logger import logger
        logger.error(f"Error al registrar alias: {e}")

def obtener_info_equipo():
    return {
        "hostname": socket.gethostname(),
        "sistema": platform.system() + " " + platform.release()
    }

def marcar_cliente_desconectado(uuid_value):
    if not requests:
        from app_logger import logger
        logger.warning("requests no disponible; no se marcará desconectado")
        return
    try:
        response = requests.post(
            "http://symbolsaps.ddns.net:8000/api/marcar_desconectado",
            json={"uuid": uuid_value},
            timeout=5
        )
        response.raise_for_status()
        from app_logger import logger
        logger.info(f"Cliente {uuid_value} marcado como desconectado.")
    except Exception as e:
        from app_logger import logger
        logger.error(f"Error al marcar cliente como desconectado: {e}")

def marcar_cliente_en_linea(uuid_value):
    try:
        response = requests.post(
            "http://symbolsaps.ddns.net:8000/api/marcar_cliente_en_linea",
            json={"uuid": uuid_value},
            timeout=5
        )
        response.raise_for_status()
        from app_logger import logger
        logger.info("Cliente marcado como en línea.")
    except Exception as e:
        from app_logger import logger
        logger.error(f"Error al marcar cliente en línea: {e}")

def obtener_ultimas_conexiones_por_tunel(uuid):
    try:
        response = requests.get(f"http://symbolsaps.ddns.net:8000/api/ultimas_conexiones/{uuid}", timeout=5)
        response.raise_for_status()
        data = response.json()
        return {item["tunnel_id"]: item["ultimo_conectado"] for item in data}
    except Exception as e:
        from app_logger import logger
        logger.error(f"Error al obtener últimas conexiones: {e}")
        return {}

def obtener_tuneles_desde_backend(client_uuid):
    response = requests.get(f"http://symbolsaps.ddns.net:8000/api/tuneles/{client_uuid}", timeout=5)
    response.raise_for_status()
    return response.json()
