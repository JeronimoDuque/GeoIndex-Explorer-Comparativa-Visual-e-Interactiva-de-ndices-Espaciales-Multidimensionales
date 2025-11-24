import sys
import os
import folium
import tempfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QTextEdit,
    QVBoxLayout, QLabel, QPushButton, QGraphicsView, QGraphicsScene, QInputDialog
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QUrl, Qt, QPointF, QObject, pyqtSlot
import json
import numpy as np
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

from trees.metrics import benchmark_gridfile, benchmark_rtree, analyze_gridfile_instance, analyze_rtree_instance
from trees.osm_loader import fetch_pois_by_bbox

from Nodes.R_tree.Point import Point
from Nodes.R_tree.Polygon import Polygon
from Nodes.R_tree.Rectangle_R import Rectangle
from trees.R_tree import RTree
from trees.Grid_file import GridFile
from trees.KD_tree import AdaptiveKDTree
from trees.Quad_tree import QuadTree
from Nodes.Rectangle_Q import Rectangle_Q
from Nodes.Bucket import Bucket


class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mapa OSM con Panel Lateral")
        self.setGeometry(400, 200, 2400, 1400)

        # mapa inicial
        self.center = [6.24, -75.58]
        mapa = folium.Map(location=self.center, zoom_start=13)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        mapa.save(temp.name)

        # Inyectar Leaflet Draw + QWebChannel JS/CSS
        with open(temp.name, 'r', encoding='utf-8') as f:
            html = f.read()

        draw_css = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"/>'
        draw_js = (
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>'
            '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'
            '<script>'
            'document.addEventListener("DOMContentLoaded", function() {'
            '  var map = null; for (var k in window) { if (k.indexOf("map_")===0) { map = window[k]; break; } }'
            '  if (!map) return; var drawnItems = new L.FeatureGroup().addTo(map); '
            '  var drawControl = new L.Control.Draw({ draw: { polygon: true, polyline:false, rectangle:false, circle:false, marker:false, circlemarker:false }, edit: { featureGroup: drawnItems } }); '
            '  map.addControl(drawControl); '
            '  map.on(L.Draw.Event.CREATED, function(e){ var layer=e.layer; drawnItems.addLayer(layer); var geo=layer.toGeoJSON(); var coords=geo.geometry.coordinates[0]; new QWebChannel(qt.webChannelTransport,function(channel){ channel.objects.bridge.sendPolygon(JSON.stringify(coords)); }); });'
            '});'
            '</script>'
        )

        if '</head>' in html:
            html = html.replace('</head>', draw_css + '\n</head>', 1)
        if '</body>' in html:
            html = html.replace('</body>', draw_js + '\n</body>', 1)
        with open(temp.name, 'w', encoding='utf-8') as f:
            f.write(html)

        self._draw_css = draw_css
        self._draw_js = draw_js
        self._map_tempfile = temp.name

        self.web_view = QWebEngineView()
        self.web_view.load(QUrl.fromLocalFile(temp.name))

        # ========= PANEL LATERAL =========
        text_panel = QTextEdit()
        text_panel.setPlaceholderText("Resultados de la consulta...")
        text_panel.setReadOnly(True)

        btn_clear = QPushButton("Limpiar mapa")
        btn_clear.clicked.connect(self.clear_map)

        info_label = QLabel("Dibuja un polígono directamente sobre el mapa (herramienta de dibujo activa).\nAl crear el polígono, las coordenadas se envían automáticamente.")
        info_label.setWordWrap(True)

        label = QLabel("Panel de información:")
        label.setStyleSheet("font-size: 16px; font-weight: bold;")

        side_layout = QVBoxLayout()
        side_layout.addWidget(label)
        side_layout.addWidget(info_label)
        side_layout.addWidget(btn_clear)
        side_layout.addWidget(text_panel)

        btn_metrics = QPushButton("Ejecutar Métricas")
        btn_metrics.clicked.connect(self.run_metrics)
        side_layout.addWidget(btn_metrics)

        btn_load_pois = QPushButton("Cargar POIs (categorías)")
        btn_load_pois.clicked.connect(self.show_category_dialog)
        side_layout.addWidget(btn_load_pois)

        if HAS_MPL:
            self.fig = Figure(figsize=(5, 4))
            self.canvas = FigureCanvas(self.fig)
            side_layout.addWidget(self.canvas)
        else:
            info_no_mpl = QLabel('matplotlib no está instalado. Ejecuta: pip install matplotlib')
            info_no_mpl.setWordWrap(True)
            side_layout.addWidget(info_no_mpl)

        # Crear RTree de ejemplo
        center_lat, center_lon = 6.24, -75.58
        self.tree = RTree()
        for i in range(8):
            lon = center_lon + i * 0.001
            lat = center_lat + i * 0.001
            r = Rectangle(lon, lat, lon + 0.0015, lat + 0.002)
            data = {"id": i, "mbr": r}
            self.tree.insert(r, data)

        # Inicializar las otras estructuras: GridFile, KD-Tree, QuadTree
        self.gridfile = GridFile(capacity=4)
        # Default a una extensión mundial; se reconfigurará en cada búsqueda
        self.gridfile.x_splits = [-180.0, 180.0]
        self.gridfile.y_splits = [-90.0, 90.0]
        self.gridfile.directory = {(0, 0): Bucket(self.gridfile.capacity)}

        self.kdtree = AdaptiveKDTree()

        # QuadTree: boundary usa (x=lon, y=lat, w,h = mitad de ancho/alto)
        self.quadtree = QuadTree(Rectangle_Q(self.center[1], self.center[0], 0.2, 0.2), capacity=4)

        self.text_panel = text_panel

        # Bridge para comunicación desde JS
        class Bridge(QObject):
            def __init__(self, window):
                super().__init__()
                self.window = window

            @pyqtSlot(str)
            def sendPolygon(self, coords_json):
                try:
                    coords = json.loads(coords_json)
                except Exception:
                    return
                pts = []
                for pair in coords:
                    lng, lat = pair[0], pair[1]
                    pts.append(Point(lng, lat))
                poly = Polygon(pts)
                resultados = self.window.tree.intersect_polygon(poly)
                if not resultados:
                    self.window.text_panel.setPlainText("No se encontraron intersecciones.")
                    return

                # Mostrar únicamente: nombre del local (si existe) y sus coordenadas (lat, lon)
                lines = []
                for item in resultados:
                    # item esperado: {'data': data_obj, 'rect': candidate_rect}
                    data_obj = item.get('data') if isinstance(item, dict) and 'data' in item else item
                    rect = item.get('rect') if isinstance(item, dict) and 'rect' in item else None

                    # Nombre: preferir tags.name si existe
                    name = None
                    if isinstance(data_obj, dict):
                        tags = data_obj.get('tags', {})
                        name = tags.get('name') or data_obj.get('id')
                    else:
                        name = getattr(data_obj, 'id', None) or str(data_obj)

                    # Coordenadas: usar el centro de la MBR si está disponible
                    lat = lon = None
                    try:
                        if rect is not None and hasattr(rect, 'xmin'):
                            lon = (rect.xmin + rect.xmax) / 2.0
                            lat = (rect.ymin + rect.ymax) / 2.0
                        elif isinstance(data_obj, dict) and 'lat' in data_obj and 'lon' in data_obj:
                            lat = data_obj.get('lat')
                            lon = data_obj.get('lon')
                    except Exception:
                        lat = lon = None

                    if name is None:
                        name = 'sin_nombre'

                    if lat is not None and lon is not None:
                        lines.append(f"{name}: {lat:.6f}, {lon:.6f}")
                    else:
                        lines.append(f"{name}: coordenadas desconocidas")

                self.window.text_panel.setPlainText("\n".join(lines))

        self.channel = QWebChannel()
        self._bridge = Bridge(self)
        self.channel.registerObject('bridge', self._bridge)
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(lambda ok: self.web_view.page().setWebChannel(self.channel))

        side_widget = QWidget()
        side_widget.setLayout(side_layout)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.web_view, 3)
        main_layout.addWidget(side_widget, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
    
    def show_category_dialog(self):
        categories = [
            'restaurant','cafe','bar','fast_food','pub','bank','atm','hospital',
            'clinic','pharmacy','school','university','supermarket','marketplace',
            'hotel','motel','guest_house','parking','fuel','library','cinema',
            'theatre','post_office','police','park','place_of_worship','bakery'
        ]
        cat, ok = QInputDialog.getItem(self, 'Seleccionar categoría', 'Categoría OSM:', categories, 0, True)
        if not ok or not cat:
            return
        limit, ok2 = QInputDialog.getInt(self, 'Límite de resultados', 'Número máximo de POIs a descargar:', 300, 10, 2000, 10)
        if not ok2:
            limit = 300
        # Preguntar tamaño del área a buscar (bbox delta en grados)
        sizes = [
            ('Pequeña (~0.5 km)', 0.005),
            ('Mediana (~1 km)', 0.01),
            ('Grande (~5 km)', 0.05),
            ('Muy grande (~20 km)', 0.2)
        ]
        labels = [s[0] for s in sizes]
        choice, ok3 = QInputDialog.getItem(self, 'Tamaño del área', 'Selecciona tamaño de búsqueda:', labels, 1, False)
        if ok3 and choice:
            bbox_delta = dict(sizes)[choice]
        else:
            bbox_delta = 0.01

        # Informar sobre limitaciones: Overpass puede devolver menos resultados que el límite solicitado
        self.text_panel.setPlainText('Iniciando descarga... (nota: Overpass puede limitar el número retornado)')
        # Preguntar en qué estructura(s) cargar los POIs
        structures = ['Todos', 'RTree', 'GridFile', 'KD-Tree', 'QuadTree']
        struct_choice, ok4 = QInputDialog.getItem(self, 'Estructura destino', 'Selecciona estructura destino para los POIs:', structures, 0, False)
        if not ok4 or not struct_choice:
            struct_choice = 'Todos'

        self.load_osm_pois(amenity=cat, limit=limit, bbox_delta=bbox_delta, target=struct_choice)
    def load_osm_pois(self, amenity='restaurant', bbox_delta=0.01, limit=300, target='Todos'):
        # Obtener el centro actual del mapa en el WebView (async) y continuar en el callback
        js = "(function(){var m=null; for(var k in window){ if(k.indexOf('map_')===0){ m=window[k]; break;} } if(!m) return null; var c=m.getCenter(); return [c.lat, c.lng]; })();"
        self.text_panel.setPlainText(f'Obteniendo centro del mapa y descargando POIs (amenity={amenity})...')
        def _on_center(res):
            try:
                if res and isinstance(res, (list, tuple)) and len(res) >= 2:
                    lat_center, lon_center = float(res[0]), float(res[1])
                    # actualizar centro local para futuras operaciones
                    self.center = [lat_center, lon_center]
                else:
                    lat_center, lon_center = self.center[0], self.center[1]
            except Exception:
                lat_center, lon_center = self.center[0], self.center[1]

            south = lat_center - bbox_delta
            north = lat_center + bbox_delta
            west = lon_center - bbox_delta
            east = lon_center + bbox_delta

            self.text_panel.setPlainText(f'Descargando POIs alrededor de {lat_center:.5f}, {lon_center:.5f} (±{bbox_delta})...')
            try:
                pois = fetch_pois_by_bbox((south, west, north, east), amenity=amenity, limit=limit)
            except Exception as e:
                self.text_panel.setPlainText(f'Error al descargar POIs: {e}')
                return

            # Insertar en RTree como pequeños rectángulos y construir nuevo mapa con marcadores
            mapa = folium.Map(location=[lat_center, lon_center], zoom_start=13)
            for p in pois:
                lat = p.get('lat')
                lon = p.get('lon')
                if lat is None or lon is None:
                    continue
                # pequeño rectángulo alrededor del punto
                r = Rectangle(lon - 0.00005, lat - 0.00005, lon + 0.00005, lat + 0.00005)
                data = {'id': f"osm_{p.get('id')}", 'tags': p.get('tags', {}), 'lat': lat, 'lon': lon, 'mbr': r}

                # Insertar condicionalmente según 'target'
                if target in ('Todos', 'RTree'):
                    try:
                        self.tree.insert(r, data)
                    except Exception:
                        pass

                if target in ('Todos', 'GridFile'):
                    try:
                        # normalizar grid a la caja de búsqueda
                        self.gridfile.x_splits = [west, east]
                        self.gridfile.y_splits = [south, north]
                        self.gridfile.directory = {(0, 0): Bucket(self.gridfile.capacity)}
                        self.gridfile.insert(lon, lat)
                    except Exception:
                        pass

                if target in ('Todos', 'KD-Tree'):
                    try:
                        self.kdtree.insert([lon, lat])
                    except Exception:
                        pass

                if target in ('Todos', 'QuadTree'):
                    try:
                        qpt = Point(lon, lat)
                        self.quadtree.insert(qpt)
                    except Exception:
                        pass

                popup = p.get('tags', {}).get('name', str(p.get('id')))
                folium.CircleMarker(location=[lat, lon], radius=3, popup=popup, color='blue', fill=True).add_to(mapa)

            # Guardar mapa temporal y reinyectar draw + channel
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            mapa.save(temp.name)
            with open(temp.name, 'r', encoding='utf-8') as f:
                html = f.read()
            if hasattr(self, '_draw_css') and '</head>' in html:
                html = html.replace('</head>', self._draw_css + '\n</head>', 1)
            if hasattr(self, '_draw_js') and '</body>' in html:
                html = html.replace('</body>', self._draw_js + '\n</body>', 1)
            with open(temp.name, 'w', encoding='utf-8') as f:
                f.write(html)

            # Cargar nuevo archivo en el WebView y reestablecer el canal
            self.web_view.load(QUrl.fromLocalFile(temp.name))
            self.web_view.loadFinished.connect(lambda ok: self.web_view.page().setWebChannel(self.channel))
            self.text_panel.setPlainText(f'Cargados {len(pois)} POIs (amenity={amenity}) alrededor del centro actual.')

        # Ejecutar JS para obtener centro y usar _on_center como callback
        try:
            self.web_view.page().runJavaScript(js, _on_center)
        except Exception:
            # fallback: usar centro guardado
            _on_center(None)
    def run_metrics(self):
        # tamaños de prueba (puedes ajustar)
        sizes = [100, 500, 2000]
        # preguntar al usuario si usar datos actuales o generar sintéticos
        choices = ['Sintético (crear datos aleatorios)', 'GridFile (usar datos actuales)', 'RTree (usar datos actuales)', 'Ambos actuales (GridFile y RTree)']
        choice, ok = QInputDialog.getItem(self, 'Fuente de datos para benchmark', 'Selecciona fuente de datos:', choices, 0, False)
        if not ok or not choice:
            choice = choices[0]

        self.text_panel.setPlainText('Ejecutando benchmarks... esto puede tardar unos segundos.')

        gf_res = None
        rt_res = None

        if choice == choices[0]:
            # sintético (comportamiento por defecto)
            gf_res = benchmark_gridfile(sizes, capacity=4)
            rt_res = benchmark_rtree(sizes, max_entries=4)
        elif choice == choices[1]:
            # usar GridFile actual
            try:
                gf_res = analyze_gridfile_instance(self.gridfile)
            except Exception as e:
                self.text_panel.setPlainText(f'Error analizando GridFile actual: {e}')
                return
        elif choice == choices[2]:
            # usar RTree actual
            try:
                rt_res = analyze_rtree_instance(self.tree)
            except Exception as e:
                self.text_panel.setPlainText(f'Error analizando RTree actual: {e}')
                return
        else:
            # ambos actuales
            try:
                gf_res = analyze_gridfile_instance(self.gridfile)
            except Exception as e:
                self.text_panel.setPlainText(f'Error analizando GridFile actual: {e}')
                return
            try:
                rt_res = analyze_rtree_instance(self.tree)
            except Exception as e:
                self.text_panel.setPlainText(f'Error analizando RTree actual: {e}')
                return

        # Dibujar gráficos: load_factor y tiempos (o mostrar instrucciones si falta matplotlib)
        if HAS_MPL:
            self.fig.clear()
            ax1 = self.fig.add_subplot(2, 1, 1)
            # Gráfico de barras para Factor de Carga
            if gf_res is not None and rt_res is not None and gf_res['sizes'] == rt_res['sizes']:
                x = np.arange(len(gf_res['sizes']))
                width = 0.35
                ax1.bar(x - width/2, gf_res['load_factors'], width, label='GridFile LF')
                ax1.bar(x + width/2, rt_res['load_factors'], width, label='RTree LF')
                ax1.set_xticks(x)
                ax1.set_xticklabels([str(s) for s in gf_res['sizes']])
            else:
                # Trazar cada conjunto en su propio offset si existen
                offset = 0.0
                if gf_res is not None:
                    xg = np.arange(len(gf_res['sizes'])) + offset
                    ax1.bar(xg, gf_res['load_factors'], 0.4, label='GridFile LF')
                    ax1.set_xticks(xg)
                    ax1.set_xticklabels([str(s) for s in gf_res['sizes']])
                    offset += len(gf_res['sizes']) + 1
                if rt_res is not None:
                    xr = np.arange(len(rt_res['sizes'])) + offset
                    ax1.bar(xr, rt_res['load_factors'], 0.4, label='RTree LF')
                    # extender etiquetas
                    ticks = list(ax1.get_xticks()) + list(xr)
                    labels = list(ax1.get_xticklabels()) + [str(s) for s in rt_res['sizes']]
                    try:
                        ax1.set_xticks(ticks)
                        ax1.set_xticklabels([lbl.get_text() if hasattr(lbl, 'get_text') else str(lbl) for lbl in labels])
                    except Exception:
                        pass

            ax1.set_ylabel('Factor de Carga')
            ax1.legend()

            ax2 = self.fig.add_subplot(2, 1, 2)
            # Gráfico de barras para tiempos
            if gf_res is not None and rt_res is not None and gf_res['sizes'] == rt_res['sizes']:
                x = np.arange(len(gf_res['sizes']))
                width = 0.35
                ax2.bar(x - width/2, gf_res['times'], width, label='GridFile time')
                ax2.bar(x + width/2, rt_res['times'], width, label='RTree time')
                ax2.set_xticks(x)
                ax2.set_xticklabels([str(s) for s in gf_res['sizes']])
            else:
                offset = 0.0
                if gf_res is not None:
                    xg = np.arange(len(gf_res['sizes'])) + offset
                    ax2.bar(xg, gf_res['times'], 0.4, label='GridFile time')
                    ax2.set_xticks(xg)
                    ax2.set_xticklabels([str(s) for s in gf_res['sizes']])
                    offset += len(gf_res['sizes']) + 1
                if rt_res is not None:
                    xr = np.arange(len(rt_res['sizes'])) + offset
                    ax2.bar(xr, rt_res['times'], 0.4, label='RTree time')

            ax2.set_xlabel('N (nº de inserciones)')
            ax2.set_ylabel('Tiempo (s)')
            ax2.legend()

            self.canvas.draw()
            self.text_panel.setPlainText('Benchmarks completos. Ver gráficos.')
        else:
            # Mostrar resumen numérico en el panel
            lines = ["matplotlib no está instalado. Instala con: pip install matplotlib", ""]
            if gf_res is not None:
                lines.append("GridFile:")
                for s, t, m, lf in zip(gf_res['sizes'], gf_res['times'], gf_res['mem_peaks'], gf_res['load_factors']):
                    lines.append(f"N={s}: time={t:.4f}s, mem_peak={m/1024:.1f} KiB, load_factor={lf:.3f}")
                lines.append("")
            if rt_res is not None:
                lines.append("RTree:")
                for s, t, m, lf in zip(rt_res['sizes'], rt_res['times'], rt_res['mem_peaks'], rt_res['load_factors']):
                    lines.append(f"N={s}: time={t:.4f}s, mem_peak={m/1024:.1f} KiB, load_factor={lf:.3f}")
            self.text_panel.setPlainText("\n".join(lines))

    def eventFilter(self, source, event):
        return super().eventFilter(source, event)
    

    def clear_map(self):
        # Ejecuta JS para limpiar las capas dibujadas (drawnItems debe existir en la página)
        js = "if (typeof drawnItems !== 'undefined') { drawnItems.clearLayers(); }"
        self.web_view.page().runJavaScript(js)
    


if __name__ == "__main__":
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"  # evita pantalla en blanco en Windows
    app = QApplication(sys.argv)
    win = MapWindow()
    win.show()
    sys.exit(app.exec_())
