# Layout automático y conversión de archivos MiraMon

Plugin para QGIS desarrollado para automatizar composiciones de mapa y convertir capas entre formatos de QGIS y MiraMon.

## ¿Qué hace?

* **Composiciones automáticas (`layout_builder.py`):** Genera layouts de mapa de forma automatizada (leyenda, escala, títulos, etc.).
* **Conversión de datos (`converter.py`):** Facilita la conversión y compatibilidad de archivos con el entorno MiraMon.

## Archivos del proyecto

* `plugin.py`: Lógica principal e interfaz del complemento en QGIS.
* `layout_builder.py`: Generación automática de maquetas/layouts.
* `converter.py`: Herramientas de conversión de formatos.
* `metadata.txt`: Configuración y metadatos del plugin.

## Instalación

Copiar la carpeta `layout_automatico_miramon` en la ruta de plugins de QGIS:

* **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`

Activar el plugin desde **Complementos > Gestionar e instalar complementos**.
