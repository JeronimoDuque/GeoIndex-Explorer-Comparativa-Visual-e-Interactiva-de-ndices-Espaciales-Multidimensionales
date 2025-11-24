import requests
import time
from typing import List, Dict, Tuple

# Simple helper para descargar POIs desde Overpass (OpenStreetMap)
# Devuelve lista de elementos {'id': id, 'lat': ..., 'lon': ..., 'tags': {...}}
# Usa bbox = (south, west, north, east)

DEFAULT_OVERPASS_ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.openstreetmap.fr/api/interpreter',
    'https://lz4.overpass-api.de/api/interpreter'
]

def _build_query(bbox: Tuple[float, float, float, float], amenity: str, limit: int, timeout: int) -> str:
    south, west, north, east = bbox
    return f"""
    [out:json][timeout:{timeout}];
    (
      node["amenity"="{amenity}"]({south},{west},{north},{east});
      way["amenity"="{amenity}"]({south},{west},{north},{east});
      relation["amenity"="{amenity}"]({south},{west},{north},{east});
    );
    out center {limit};
    """


def fetch_pois_by_bbox(bbox: Tuple[float, float, float, float], amenity: str = 'restaurant', limit: int = 500,
                       timeout: int = 25, endpoints: List[str] = None, max_retries: int = 3) -> List[Dict]:
    """Intentar descargar POIs usando varios endpoints y varios reintentos.

    Parámetros:
    - bbox: (south, west, north, east)
    - amenity: categoría OSM
    - limit: máximo resultados solicitados a Overpass
    - timeout: tiempo de espera por petición
    - endpoints: lista de endpoints Overpass (si None, se usan DEFAULT_OVERPASS_ENDPOINTS)
    - max_retries: reintentos por endpoint (con backoff exponencial)

    Lanza RuntimeError si no se pudo obtener respuesta válida.
    """
    if endpoints is None:
        endpoints = DEFAULT_OVERPASS_ENDPOINTS

    query = _build_query(bbox, amenity, limit, timeout)

    last_error = None
    for ep in endpoints:
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.post(ep, data={'data': query}, timeout=timeout + 5)
                r.raise_for_status()
                data = r.json()
                # éxito: parsear elementos
                results = []
                for elem in data.get('elements', []):
                    if elem.get('type') == 'node':
                        lat = elem.get('lat')
                        lon = elem.get('lon')
                    else:
                        center = elem.get('center')
                        if center is None:
                            continue
                        lat = center.get('lat')
                        lon = center.get('lon')
                    if lat is None or lon is None:
                        continue
                    results.append({'id': elem.get('id'), 'lat': lat, 'lon': lon, 'tags': elem.get('tags', {})})
                return results
            except Exception as e:
                last_error = e
                # Si es último intento para este endpoint, probar el siguiente endpoint
                if attempt < max_retries:
                    backoff = 1.0 * (2 ** (attempt - 1))
                    time.sleep(backoff)
                    continue
                else:
                    break

    raise RuntimeError(f"Error fetching OSM data (tried {len(endpoints)} endpoints): {last_error}")

