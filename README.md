 Sistema de Análisis de Suelos para Plantaciones

Sistema de evaluación de calidad de suelos basado en imágenes satelitales para plantaciones costeras de Ecuador usando Google Earth Engine.

 Descripción General

Este sistema recupera imágenes del satélite Sentinel-2, aplica máscaras de nubes, crea composiciones temporales y calcula índices de calidad de suelo para análisis de tierras agrícolas.

Características

- **Eliminación de Nubes**: Usa el modelo de machine learning s2cloudless para detección precisa de nubes
- **Composición Temporal**: Combina múltiples imágenes para llenar vacíos y reducir ruido
- **Índices de Suelo**: Calcula múltiples índices para evaluación de tipo y calidad de suelo
- **Compatible con Tier Gratuito**: Diseñado para funcionar dentro de los límites gratuitos de GEE
- **Diseño Modular**: Fácil de extender y personalizar

Estructura del Proyecto

```
plantation_soil_analysis/
├── config.py           # Parámetros de configuración
├── auth.py             # Autenticación con GEE
├── retrieval.py        # Recuperación de imágenes satelitales
├── cloud_masking.py    # Funciones de eliminación de nubes
├── compositing.py      # Creación de composiciones temporales
├── soil_indices.py     # Cálculo de índices de suelo
├── compression.py      # Formateo de exportación
├── export.py           # Guardar en Drive/Cloud
├── main.py             # Script principal de orquestación
└── requirements.txt    # Dependencias de Python
```

Instalación

1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

2. Autenticarse con Google Earth Engine

Si no tienes una cuenta de GEE:
1. Ve a https://earthengine.google.com/
2. Regístrate para una cuenta gratuita no comercial
3. Espera la aprobación (usualmente unas horas)

Luego autentícate:
```bash
earthengine authenticate --auth_mode=notebook
```

Después de autenticar, configura tu proyecto:
```bash
earthengine set_project TU_PROYECTO_ID
```

3. Configurar Parámetros

Edita `config.py` para establecer:
- **Coordenadas**: Ubicación de tu plantación
- **Rango de fechas**: Período de análisis
- **Umbral de nubes**: Tolerancia para cobertura de nubes
- **Configuración de exportación**: Destino y formato de salida

Uso

Análisis Básico

```bash
python main.py
```

Esto:
1. Recupera imágenes Sentinel-2 para la ubicación configurada
2. Aplica máscara de nubes
3. Crea una composición mediana
4. Calcula índices de suelo
5. Muestra estadísticas e interpretación

Verificar Imágenes Disponibles

```bash
python main.py --info
```

Muestra cuántas imágenes están disponibles sin procesar.

Exportar Resultados

```bash
python main.py --export
```

Exporta a Google Drive:
- Visualización RGB (color verdadero)
- Composición SWIR (suelo/geología)
- Índices de suelo (GeoTIFF)
- Bandas espectrales completas

Esperar a que Terminen las Exportaciones

```bash
python main.py --export --wait
```

Ubicación Personalizada

```bash
python main.py --lat -1.85 --lon -80.75 --buffer 2000
```

Opciones de Línea de Comandos

| Opción | Descripción |
|--------|-------------|
| `--info` | Solo mostrar información de imágenes disponibles |
| `--export` | Exportar resultados a Google Drive |
| `--wait` | Esperar a que las exportaciones terminen |
| `--no-stats` | Omitir cálculo de estadísticas |
| `--lat` | Sobrescribir latitud |
| `--lon` | Sobrescribir longitud |
| `--buffer` | Sobrescribir radio del buffer en metros |

Bandas de Sentinel-2

Bandas Utilizadas para Análisis de Suelo

| Banda | Resolución | Uso |
|-------|------------|-----|
| B2 (Azul) | 10m | Discriminación suelo/vegetación, materia orgánica |
| B3 (Verde) | 10m | Índice de color, turbidez |
| B4 (Rojo) | 10m | Identificación de suelo, óxido de hierro |
| B8 (NIR) | 10m | Biomasa, humedad, vegetación |
| B11 (SWIR 1) | 20m | **Crítico** — humedad del suelo, minerales de arcilla |
| B12 (SWIR 2) | 20m | **Crítico** — humedad del suelo, contenido mineral |

Combinaciones de Visualización

| Combinación | Bandas | Qué Muestra |
|-------------|--------|-------------|
| Color Verdadero | B4, B3, B2 | Colores naturales como los vería el ojo |
| Falso Color Agricultura | B8, B4, B3 | Vegetación en rojo brillante, suelo en marrón |
| Composición SWIR Suelo | B11, B8, B4 | Suelo en rosa/magenta, humedad en oscuro |

Índices de Suelo

| Índice | Nombre | Fórmula | Interpretación |
|--------|--------|---------|----------------|
| NDSI | Índice de Suelo Normalizado | (SWIR-NIR)/(SWIR+NIR) | Mayor = más suelo expuesto |
| BI | Índice de Suelo Desnudo | ((SWIR+Rojo)-(NIR+Azul))/((SWIR+Rojo)+(NIR+Azul)) | Resalta suelo expuesto |
| BSI | Índice de Suelo Desnudo (alt) | Escalado 0-200 | >100 indica suelo expuesto |
| CI | Índice de Color | (Rojo-Verde)/(Rojo+Verde) | Contenido de óxido de hierro |
| NDMI | Índice de Humedad | (NIR-SWIR)/(NIR+SWIR) | Humedad del suelo/vegetación |
| ClayIndex | Índice de Arcilla | SWIR1/SWIR2 | Indicador de contenido de arcilla |
| SOM_Index | Índice de Materia Orgánica | Basado en bandas visibles | Proxy de contenido orgánico |

Interpretación de Resultados

Cobertura Vegetal (NDVI)
- < 0.2: Escasa/desnuda — ideal para análisis de suelo
- 0.2-0.4: Cobertura moderada — suelo parcialmente visible
- > 0.4: Vegetación densa — suelo puede estar oscurecido

Humedad (NDMI)
- < 0: Condiciones secas
- 0-0.2: Humedad moderada
- > 0.2: Alta humedad

### Color del Suelo (CI)
- Positivo: Suelo rojizo (oxidación de hierro, bien drenado)
- Negativo: Suelo más oscuro/verdoso
- Cercano a cero: Neutral

### Índice de Suelo Desnudo (BSI)
- < 100: Bajo índice de suelo desnudo (vegetación presente)
- 100-120: Suelo desnudo moderado
- > 120: Alta exposición de suelo desnudo

### Interpretación de Colores en Imagen SWIR

| Color en Imagen | Significado |
|-----------------|-------------|
| Verde brillante | Vegetación sana y densa |
| Marrón/Oliva | Vegetación escasa, pasto seco |
| Rosa/Magenta | Suelo desnudo seco |
| Naranja/Rojo | Suelo muy seco, arena |
| Áreas oscuras | Suelo húmedo o agua |

## Consejos para Ecuador

1. **Temporada Seca**: Julio-Noviembre en la costa tiene menos cobertura de nubes
2. **Múltiples Fechas**: Usa al menos 3 meses para buenas composiciones
3. **Sentinel-1 SAR**: Usar como respaldo cuando persisten las nubes
4. **Imágenes de Mañana**: Frecuentemente más claras que las de la tarde
5. **Umbral de Nubes**: Empieza con 40%, aumenta si no hay suficientes imágenes

## Extendiendo el Sistema

### Agregar Nuevos Índices

Edita `soil_indices.py`:

```python
def calculate_mi_indice(image):
    banda1 = image.select(config.S2_BANDS["nir"])
    banda2 = image.select(config.S2_BANDS["swir_1"])
    resultado = banda1.divide(banda2).rename("MiIndice")
    return resultado
```

Luego agrégalo a `config.SOIL_INDICES`.

### Agregar Nuevas Ubicaciones

Edita `config.py` o usa línea de comandos:
```bash
python main.py --lat TU_LAT --lon TU_LON
```

### Procesamiento por Lotes

```python
from main import run_pipeline
from retrieval import create_region_of_interest

ubicaciones = [
    (-1.84, -80.74, "plantacion_a"),
    (-1.90, -80.80, "plantacion_b"),
    (-2.10, -80.50, "plantacion_c"),
]

for lat, lon, nombre in ubicaciones:
    print(f"\nProcesando {nombre}...")
    roi = create_region_of_interest(lat, lon)
    results = run_pipeline(roi, do_export=True)
```

## Archivos de Salida

| Archivo | Contenido | Uso |
|---------|-----------|-----|
| `*_rgb.tif` | Imagen color verdadero | Visualización general |
| `*_soil_swir.tif` | Composición SWIR | Ver variaciones de suelo |
| `*_soil_indices.tif` | Índices calculados | Análisis cuantitativo |
| `*_spectral.tif` | Todas las bandas | Análisis avanzado |

## Solución de Problemas

### No se encontraron imágenes
- Extiende el rango de fechas
- Aumenta `MAX_SCENE_CLOUD_PERCENT` en config.py
- Verifica que las coordenadas sean correctas

### Errores de autenticación
- Ejecuta `earthengine authenticate --auth_mode=notebook`
- Verifica que tu cuenta de GEE esté aprobada
- Asegúrate de configurar el proyecto: `earthengine set_project TU_PROYECTO`

### Falla la exportación
- Reduce `BUFFER_RADIUS_M`
- Aumenta `EXPORT_SCALE` (menor resolución)
- Verifica que Google Drive tenga espacio

### Imágenes granuladas/pixeladas
- Es la resolución nativa de Sentinel-2 (10-20m)
- Aumenta el área con `--buffer 5000` para mejor contexto
- Para mayor resolución necesitarías datos comerciales (Planet, Maxar)

## Variables de Entorno

```bash
# Opcional: configurar proyecto por defecto
export GEE_PROJECT=tu_proyecto_id

# Opcional: usar cuenta de servicio
export GEE_KEY_FILE=/ruta/a/tu/clave.json
export GEE_SERVICE_ACCOUNT=cuenta@proyecto.iam.gserviceaccount.com
```

## Requisitos del Sistema

- Python 3.8+
- Cuenta de Google Earth Engine (gratuita para uso no comercial)
- Conexión a internet
- ~50MB de espacio en disco para dependencias

## Licencia

Licencia MIT - Siéntete libre de usar y modificar.

## Referencias

- [Documentación de Google Earth Engine](https://developers.google.com/earth-engine)
- [Guía de Usuario de Sentinel-2](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi)
- [s2cloudless](https://medium.com/sentinel-hub/cloud-masks-at-your-service-6e5b2cb2ce8a)
- [Índices Espectrales para Suelos](https://www.indexdatabase.de/)

## Contacto y Soporte

Para problemas o sugerencias, revisa la documentación de GEE o los recursos de Sentinel-2 listados arriba.
