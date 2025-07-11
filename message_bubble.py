# message_bubble.py
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from datetime import datetime


def colored_pixmap(svg_path, color, size=16):
    """Return a QPixmap with the given SVG colored."""
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()

    return pixmap

class MessageBubble(QWidget):
    def __init__(self, text, sender, is_sender, timestamp=None, url=None, link_handler=None):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)

        # Nombre
        if not is_sender:
            name_label = QLabel(sender)
            name_label.setStyleSheet("color: #555; font-weight: bold; font-size: 10px;")
            layout.addWidget(name_label)

        # Texto (puede incluir enlace)
        if url:
            bubble_widget = QWidget()
            bubble_layout = QHBoxLayout(bubble_widget)
            bubble_layout.setContentsMargins(6, 6, 6, 6)
            bubble_layout.setSpacing(6)

            icon_label = QLabel()
            icon_pix = QPixmap("assets/icons/file.svg").scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(icon_pix)
            icon_label.setFixedSize(48, 48)
            bubble_layout.addWidget(icon_label)

            text_label = QLabel()
            text_label.setText(f'<a href="{url}" style="color:white; text-decoration:none;">{text}</a>')
            text_label.setTextFormat(Qt.RichText)
            text_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            text_label.setOpenExternalLinks(False)
            text_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
            text_label.setWordWrap(True)
            if link_handler:
                text_label.linkActivated.connect(lambda _: link_handler(url, text))
            bubble_layout.addWidget(text_label)

            bubble_widget.setStyleSheet(
                """
                background-color: #00BCD4;
                border-radius: 8px;
            """ if is_sender else """
                background-color: #444;
                border-radius: 8px;
            """
            )
            layout.addWidget(bubble_widget)
        else:
            text_label = QLabel(text)
            text_label.setWordWrap(True)
            text_label.setStyleSheet(
                """
                color: #FFF;
                padding: 6px;
                background-color: #00BCD4;
                border-radius: 8px;
            """ if is_sender else """
                color: #FFF;
                padding: 6px;
                background-color: #444;
                border-radius: 8px;
            """
            )
            layout.addWidget(text_label)

        # Hora
        if timestamp:
            hora = datetime.fromtimestamp(timestamp / 1000).strftime('%H:%M')
            time_label = QLabel(hora)
            time_label.setStyleSheet("color: #999; font-size: 9px;")
            time_label.setAlignment(Qt.AlignRight)
            layout.addWidget(time_label)

        self.setLayout(layout)

        # Alineación
        if is_sender:
            layout.setAlignment(Qt.AlignRight)
        else:
            layout.setAlignment(Qt.AlignLeft)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
