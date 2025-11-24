import sys
import folium
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import tempfile
import os

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mapa OpenStreetMap con Python")
        self.setGeometry(100, 100, 800, 600)

        # Crear el mapa Folium
        mapa = folium.Map(
            location=[6.2442, -75.5812],   # Medellín, cambia por tu región
            zoom_start=13,
            tiles="OpenStreetMap"
        )

        # Guardar el mapa en un archivo temporal
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        mapa.save(temp.name)

        # Crear widget web
        self.web_view = QWebEngineView()
        self.web_view.load(QUrl.fromLocalFile(temp.name))
        self.setCentralWidget(self.web_view)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec_())
