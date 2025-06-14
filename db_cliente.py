import mysql.connector
import os
import requests
import uuid
import socket
import platform

def get_connection():
    return mysql.connector.connect(
        host='symbolsaps.ddns.net',
        user='admin',
        password='Febrero2025*-+',
        database='securex'
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
        print(f"🆕 UUID generado: {new_uuid}")
        return new_uuid
    else:
        with open(path, "r") as f:
            return f.read().strip()

def registrar_cliente(uuid_value, hostname, sistema):
    try:
        response = requests.post(
            "http://symbolsaps.ddns.net:8000/api/registrar_cliente",
            json={
                "uuid": uuid_value,
                "hostname": hostname,
                "sistema": sistema
            }
        )
        response.raise_for_status()
        print("✅ Cliente registrado correctamente en el backend.")
    except Exception as e:
        print(f"❌ Error al registrar cliente en el backend: {e}")

def registrar_alias_cliente(uuid_value, tunnel_id, alias):
    payload = {
        "uuid": uuid_value,
        "tunnel_id": tunnel_id,
        "alias": alias
    }
    try:
        response = requests.post("http://symbolsaps.ddns.net:8000/api/registrar_alias", json=payload)
        response.raise_for_status()
        print("✅ Alias registrado correctamente")
    except Exception as e:
        print("❌ Error al registrar alias:", e)

def obtener_info_equipo():
    return {
        "hostname": socket.gethostname(),
        "sistema": platform.system() + " " + platform.release()
    }
