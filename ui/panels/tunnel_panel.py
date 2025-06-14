from PyQt5.QtWidgets import ( QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QHBoxLayout,
QFileDialog, QMessageBox, QScrollArea, QFrame, QSpacerItem, QSizePolicy, QDialog, QFormLayout, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QVariantAnimation, pyqtProperty
from PyQt5.QtGui import QColor, QPalette
import base64, json
from tunnel_client import TunnelClient
from db_cliente import obtener_tunel_por_nombre
from password_utils import verificar_password
from chat_window import ChatWindow


class TunnelCard(QFrame):
    def __init__(self, nombre, on_click):
        super().__init__()

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        self.title = QLabel(nombre)
        self.title.setStyleSheet("font-size: 13px; color: white;")
        self.title.setTextInteractionFlags(Qt.NoTextInteraction)

        self.subtitle = QLabel("Fecha de creación")
        self.subtitle.setStyleSheet("font-size: 10px; color: gray;")
        self.subtitle.setTextInteractionFlags(Qt.NoTextInteraction)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)

        # Color inicial
        self.base_color = QColor("#1f1f1f")
        self.setAutoFillBackground(True)
        self._update_background(self.base_color)

        # Evento de clic con animación
        self.mousePressEvent = lambda event: self._click_animation(on_click)

    def _click_animation(self, callback):
        animation = QVariantAnimation(
            startValue=QColor("#00BCD4"),  # celeste al hacer clic
            endValue=self.base_color,
            duration=200  # en milisegundos
        )
        animation.valueChanged.connect(self._update_background)
        animation.finished.connect(callback)
        animation.start()
        self._animation = animation  # evitar GC inmediato

    def _update_background(self, color):
        palette = self.palette()
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)

class TunnelPanel(QWidget):
    def __init__(self, uuid, hostname, sistema, parent=None):
        super().__init__(parent)
        self.uuid = uuid
        self.hostname = hostname
        self.sistema = sistema
        self.parent = parent
        self.conexiones_tuneles = {}
        self.participants = {}
        self.files = {}
        self.cliente = None

        from db_cliente import get_client_uuid
        _ = get_client_uuid()  # 👈 Esto asegura que se registre el cliente

        main_layout = QHBoxLayout(self)

        # ==== PANEL IZQUIERDO (Túneles) ====
        self.left_panel = QVBoxLayout()
        self.left_panel.setSpacing(10)

        search_layout = QHBoxLayout()

        search_input = QLineEdit()
        search_input.setPlaceholderText("Buscar túnel")
        search_input.setStyleSheet("padding: 4px; background-color: #222; border: none; color: white;")
        search_layout.addWidget(search_input)

        # Botón +
        btn_mas = QPushButton("＋")
        btn_mas.setFixedWidth(50)
        btn_mas.setStyleSheet("color: #00BCD4; font-size: 18px; background-color: #333; border: none;")
        btn_mas.setCursor(Qt.PointingHandCursor)
        search_layout.addWidget(btn_mas)

        # Conectar la acción del botón
        btn_mas.clicked.connect(self.mostrar_menu_tunel)

        self.left_panel.addLayout(search_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFixedWidth(320)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_widget)
        self.left_panel.addWidget(self.scroll_area)

        left_container = QWidget()
        left_container.setLayout(self.left_panel)
        left_container.setFixedWidth(340)
        main_layout.addWidget(left_container)

        # ==== PANEL CENTRAL (Chat) ====
        from PyQt5.QtWidgets import QTabWidget

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.cerrar_pestana_tunel)
        self.tab_widget.currentChanged.connect(self._tab_changed)
        main_layout.addWidget(self.tab_widget, 4)

        # ==== PANEL DERECHO (Participantes y Archivos) ====
        right_panel = QVBoxLayout()

        label_participantes = QLabel("Participantes")
        label_participantes.setStyleSheet("background: transparent; color: white; font-weight: bold;")
        right_panel.addWidget(label_participantes)

        self.users_list = QListWidget()
        self.users_list.setFixedWidth(215)
        right_panel.addWidget(self.users_list)

        label_archivos = QLabel("Archivos")
        label_archivos.setStyleSheet("background: transparent; color: white; font-weight: bold;")
        right_panel.addWidget(label_archivos)

        self.files_list = QListWidget()
        self.files_list.setFixedWidth(215)
        self.files_list.itemDoubleClicked.connect(self._download_file_from_list)
        right_panel.addWidget(self.files_list)

        right_container = QWidget()
        right_container.setLayout(right_panel)
        right_container.setFixedWidth(240)
        main_layout.addWidget(right_container)

        self.actualizar_lista_tuneles()

    # FUNCIONES!!!!

    def crear_tunel_desde_ui(self):
        import requests
        nombre = self.input_name.text().strip()
        clave = self.input_password.text().strip()
        if not nombre or not clave:
            QMessageBox.warning(self, "Error", "Nombre y contraseña requeridos")
            return
        try:
            from db_cliente import get_client_uuid
            uuid = get_client_uuid()

            response = requests.post("http://symbolsaps.ddns.net:8000/api/tunnels/create", json={
                "name": nombre,
                "password": clave,
                "uuid": uuid  # 👈 necesario para que el backend lo reciba
            })

            if response.status_code == 201:
                QMessageBox.information(self, "Túnel creado", f"🔐 Túnel '{nombre}' creado exitosamente.")
                self.actualizar_lista_tuneles()
            else:
                raise Exception(response.text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear el túnel:\n{e}")

    def actualizar_lista_tuneles(self):
        import requests
        self.scroll_clear()
        try:
            response = requests.get("http://symbolsaps.ddns.net:8000/api/tunnels")
            if response.status_code == 200:
                tuneles = response.json()
                for tunel in tuneles:
                    card = TunnelCard(tunel["name"], lambda t=tunel: self.unirse_a_tunel(t))
                    self.scroll_layout.addWidget(card)
            else:
                raise Exception("No se pudo obtener la lista de túneles")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"⚠️ Error cargando túneles: {e}")

    def scroll_clear(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def unirse_a_tunel(self, tunel):
        from PyQt5.QtWidgets import QDialog, QFormLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Conectarse al túnel")
        layout = QFormLayout(dialog)

        input_alias = QLineEdit()
        input_password = QLineEdit()
        input_password.setEchoMode(QLineEdit.Password)

        layout.addRow("Alias:", input_alias)
        layout.addRow("Contraseña:", input_password)

        btn_ok = QPushButton("Conectar")
        btn_ok.clicked.connect(dialog.accept)
        layout.addWidget(btn_ok)

        if not dialog.exec_():
            return

        alias = input_alias.text().strip()
        password = input_password.text().strip()

        if not alias or not password:
            QMessageBox.warning(self, "Error", "Alias y contraseña son requeridos")
            return

        import requests
        try:
            response = requests.post("http://symbolsaps.ddns.net:8000/api/tunnels/join", json={
                "tunnel_id": tunel["id"],
                "password": password,
                "alias": alias
            })
            if response.status_code != 200:
                raise Exception(response.text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Validación fallida:\n{e}")
            return

        try:
            nombre = tunel["name"]  # ✅ Aquí se define

            from db_cliente import get_client_uuid, registrar_alias_cliente
            uuid = get_client_uuid()

            self.cliente = TunnelClient(
                host="symbolsaps.ddns.net",
                port=5050,
                tunnel_id=tunel["id"],
                alias=alias,
                uuid=uuid,  # ✅ Aquí se pasa el uuid requerido
                on_receive_callback=self.recibir_mensaje
            )

            self.cliente.connect()
            registrar_alias_cliente(uuid, tunel["id"], alias)

            tab = QWidget()
            layout = QVBoxLayout(tab)

            header_layout = QHBoxLayout()
            label = QLabel(f"🟢 {nombre} como {alias}")
            label.setStyleSheet("color: white; font-weight: bold;")
            btn_close = QPushButton("Desconectar")
            btn_close.setStyleSheet("background-color: red; color: white; padding: 2px;")
            btn_close.clicked.connect(lambda: self.desconectar_tunel(tab, tunel['id']))
            header_layout.addWidget(label)
            header_layout.addStretch()
            header_layout.addWidget(btn_close)

            from chat_window import ChatWindow
            chat_window = ChatWindow(
                alias=alias,
                client=self.cliente,
                tunnel_id=tunel["id"],
                uuid=uuid,
                on_file_event=self.handle_file_event,
            )

            layout.addLayout(header_layout)
            layout.addWidget(chat_window)

            self.tab_widget.addTab(tab, nombre)
            self.tab_widget.setCurrentWidget(tab)

            self.conexiones_tuneles[tunel["id"]] = {
                "cliente": self.cliente,
                "chat": chat_window,
                "tab": tab,
                "alias": alias,
            }

            self.fetch_participants(tunel["id"])
            self.fetch_files(tunel["id"])
            self.update_side_lists(tunel["id"])

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error de conexión:\n{e}")

    def recibir_mensaje(self, mensaje):
        try:
            try:
                data = json.loads(mensaje)
            except json.JSONDecodeError:
                import ast
                data = ast.literal_eval(mensaje)
            tunel_id = data.get("tunnel_id")

            if tunel_id not in self.conexiones_tuneles:
                print("⚠️ Mensaje recibido de túnel desconocido")
                return

            chat = self.conexiones_tuneles[tunel_id]["chat"]
            chat.procesar_mensaje(mensaje)

        except Exception as e:
            print("⚠️ Error al procesar mensaje:", e)

    
    def mostrar_menu_tunel(self):
        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu(self)

        accion_crear = QAction("➕ Crear túnel", self)
        accion_conectar = QAction("🔗 Conectarse a túnel", self)

        accion_crear.triggered.connect(self.mostrar_dialogo_crear_tunel)
        accion_conectar.triggered.connect(self.mostrar_dialogo_conectar_tunel)

        menu.addAction(accion_crear)
        menu.addAction(accion_conectar)

        # Mostrar menú debajo del botón
        cursor_pos = self.mapFromGlobal(self.cursor().pos())
        menu.exec_(self.mapToGlobal(cursor_pos))

    def mostrar_dialogo_crear_tunel(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Crear túnel")
        layout = QFormLayout(dialog)

        self.input_name = QLineEdit()
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)

        layout.addRow("Nombre:", self.input_name)
        layout.addRow("Contraseña:", self.input_password)

        btn_ok = QPushButton("Crear")
        btn_ok.clicked.connect(lambda: [dialog.accept(), self.crear_tunel_desde_ui()])
        layout.addWidget(btn_ok)

        dialog.exec_()

    def mostrar_dialogo_conectar_tunel(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Conectarse a túnel")
        layout = QFormLayout(dialog)

        input_nombre = QLineEdit()
        input_alias = QLineEdit()
        input_password = QLineEdit()
        input_password.setEchoMode(QLineEdit.Password)

        layout.addRow("Nombre del túnel:", input_nombre)
        layout.addRow("Alias:", input_alias)
        layout.addRow("Contraseña:", input_password)

        btn_ok = QPushButton("Conectar")
        layout.addWidget(btn_ok)

        btn_ok.clicked.connect(lambda: self._conectar_a_tunel_manual(
            dialog, input_nombre.text().strip(),
            input_alias.text().strip(),
            input_password.text().strip()
        ))

        dialog.exec_()

    def _conectar_a_tunel_manual(self, dialog, nombre, alias, password):
        import requests
        if not nombre or not alias or not password:
            QMessageBox.warning(self, "Error", "Todos los campos son requeridos")
            return

        try:
            response = requests.get("http://symbolsaps.ddns.net:8000/api/tunnels")
            if response.status_code != 200:
                raise Exception("Error al consultar túneles")

            tuneles = response.json()
            tunel = next((t for t in tuneles if t["name"] == nombre), None)
            if not tunel:
                raise Exception("Túnel no encontrado")

            join_resp = requests.post("http://symbolsaps.ddns.net:8000/api/tunnels/join", json={
                "tunnel_id": tunel["id"],
                "password": password,
                "alias": alias
            })
            if join_resp.status_code != 200:
                raise Exception(join_resp.text)
            
            nombre = tunel["name"]
            from db_cliente import get_client_uuid, registrar_alias_cliente
            uuid = get_client_uuid()

            self.cliente = TunnelClient(
                host="symbolsaps.ddns.net",
                port=5050,
                tunnel_id=tunel["id"],
                alias=alias,
                uuid=uuid,  # ✅ Aquí se pasa el uuid requerido
                on_receive_callback=self.recibir_mensaje
            )

            self.cliente.connect()
            registrar_alias_cliente(uuid, tunel["id"], alias)

            # Crear la pestaña visual del chat
            tab = QWidget()
            layout = QVBoxLayout(tab)

            header_layout = QHBoxLayout()
            label = QLabel(f"🟢 {nombre} como {alias}")
            label.setStyleSheet("color: white; font-weight: bold;")
            btn_close = QPushButton("Desconectar")
            btn_close.setStyleSheet("background-color: red; color: white; padding: 2px;")
            btn_close.clicked.connect(lambda: self.desconectar_tunel(tab, tunel['id']))
            header_layout.addWidget(label)
            header_layout.addStretch()
            header_layout.addWidget(btn_close)

            from chat_window import ChatWindow
            chat_window = ChatWindow(
                alias=alias,
                client=self.cliente,
                tunnel_id=tunel["id"],
                uuid=uuid,
                on_file_event=self.handle_file_event,
            )

            layout.addLayout(header_layout)
            layout.addWidget(chat_window)

            self.tab_widget.addTab(tab, nombre)
            self.tab_widget.setCurrentWidget(tab)

            self.conexiones_tuneles[tunel["id"]] = {
                "cliente": self.cliente,
                "chat": chat_window,
                "chat_area": chat_window.chat_area,  # compatibilidad
                "tab": tab,
                "alias": alias,
            }

            self.fetch_participants(tunel["id"])
            self.fetch_files(tunel["id"])
            self.update_side_lists(tunel["id"])

            dialog.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def desconectar_tunel(self, tab, tunel_id):
        if tunel_id in self.conexiones_tuneles:
            cliente = self.conexiones_tuneles[tunel_id]["cliente"]
            try:
                cliente.socket.close()
            except:
                pass
            del self.conexiones_tuneles[tunel_id]
            self.participants.pop(tunel_id, None)
            self.files.pop(tunel_id, None)
        idx = self.tab_widget.indexOf(tab)
        if idx >= 0:
            self.tab_widget.removeTab(idx)
        if not self.tab_widget.count():
            self.users_list.clear()
            self.files_list.clear()

    def cerrar_pestana_tunel(self, index):
        tab = self.tab_widget.widget(index)
        for tunel_id, data in self.conexiones_tuneles.items():
            if data.get("tab") == tab:
                self.desconectar_tunel(tab, tunel_id)
                break

    def enviar_mensaje_tunel(self, tunel_id, mensaje, chat_area, input_field):
        if not mensaje.strip():
            return

        if tunel_id not in self.conexiones_tuneles:
            QMessageBox.warning(self, "Error", "Túnel no encontrado")
            return

        cliente = self.conexiones_tuneles[tunel_id]["cliente"]
        try:
            cliente.socket.sendall(mensaje.encode())
            chat_area.append(f"{mensaje}")
            input_field.clear()
        except Exception as e:
            chat_area.append(f"⚠️ Error al enviar mensaje: {e}")

    # ---- Gestión de participantes y archivos ----
    def current_tunnel_id(self):
        tab = self.tab_widget.currentWidget()
        for tid, data in self.conexiones_tuneles.items():
            if data.get("tab") == tab:
                return tid
        return None

    def _tab_changed(self, index):
        tid = self.current_tunnel_id()
        if tid:
            self.update_side_lists(tid)

    def fetch_participants(self, tunnel_id):
        """Fill ``self.participants`` with a list of aliases for ``tunnel_id``."""
        import requests
        current_alias = self.conexiones_tuneles.get(tunnel_id, {}).get("alias")
        participantes = []
        try:
            resp = requests.get(
                f"http://symbolsaps.ddns.net:8000/api/tunnels/{tunnel_id}/participants"
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    participantes = (
                        data.get("participants")
                        or data.get("data")
                        or list(data)
                    )
                else:
                    participantes = data
        except Exception as e:
            print("⚠️ Error obteniendo participantes:", e)

        if not isinstance(participantes, list):
            participantes = [participantes]

        # Añadir nuestro propio alias si no está presente
        if current_alias and all(
            (isinstance(p, dict) and p.get("alias") != current_alias)
            or (not isinstance(p, dict) and p != current_alias)
            for p in participantes
        ):
            participantes.append({"alias": current_alias})

        self.participants[tunnel_id] = participantes

    def fetch_files(self, tunnel_id):
        import requests
        try:
            resp = requests.get(f"http://symbolsaps.ddns.net:8000/api/tunnels/{tunnel_id}/files")
            if resp.status_code == 200:
                self.files[tunnel_id] = resp.json()
            else:
                self.files[tunnel_id] = []
        except Exception as e:
            print("⚠️ Error obteniendo archivos:", e)
            self.files[tunnel_id] = []

    def update_side_lists(self, tunnel_id):
        self.users_list.clear()
        for usuario in self.participants.get(tunnel_id, []):
            alias = usuario.get("alias") if isinstance(usuario, dict) else usuario
            current_alias = self.conexiones_tuneles.get(tunnel_id, {}).get("alias")
            if alias == current_alias:
                alias = f"{alias} (tú)"
            self.users_list.addItem(alias)

        self.files_list.clear()
        for archivo in self.files.get(tunnel_id, []):
            nombre = archivo.get("filename") if isinstance(archivo, dict) else archivo
            item = QListWidgetItem(nombre)
            item.setData(Qt.UserRole, archivo)
            self.files_list.addItem(item)

    def handle_file_event(self, tunnel_id, nombre, url):
        entry = {"filename": nombre, "url": url}
        self.files.setdefault(tunnel_id, []).append(entry)
        if self.current_tunnel_id() == tunnel_id:
            item = QListWidgetItem(nombre)
            item.setData(Qt.UserRole, entry)
            self.files_list.addItem(item)

    def _download_file_from_list(self, item):
        info = item.data(Qt.UserRole)
        if not isinstance(info, dict):
            return
        url = info.get("url")
        nombre = info.get("filename") or info.get("name")
        tid = self.current_tunnel_id()
        if tid and tid in self.conexiones_tuneles:
            chat = self.conexiones_tuneles[tid].get("chat")
            if chat:
                chat.download_file(url, nombre)

