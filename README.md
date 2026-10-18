# Análisis de Datos · Ventas de retail (Equipo 1)

Proyecto de Business Intelligence del curso Análisis de Datos (ITM, 2026-2) sobre las
ventas de la tienda *Superstore*.

**Dataset:** [Superstore Sales Dataset — Kaggle](https://www.kaggle.com/datasets/rohitsahoo/sales-forecasting) (archivo `train.csv`)

## Estructura

```
datos/                         # aquí va train.csv (no se sube al repositorio)
fase_1_comprension_problema/   # notebook de la Fase 1
requirements.txt               # dependencias de Python
```

## Cómo ver y ejecutar los notebooks

Antes de ejecutar, descarga `train.csv` desde Kaggle (hay que iniciar sesión) y guárdalo
en la carpeta `datos/`.

### Opción 1 · Solo verlo en GitHub

Abre el archivo `.ipynb` en GitHub: se muestra con los resultados ya ejecutados y no
hace falta instalar nada.

### Opción 2 · Jupyter en tu computador

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter lab
```

En el navegador abre `fase_1_comprension_problema/1_comprension_problema.ipynb` y
ejecuta todas las celdas (*Run → Run All Cells*).

### Opción 3 · Visual Studio Code

1. Instala las extensiones **Python** y **Jupyter**.
2. Crea el entorno e instala las dependencias como en la opción 2.
3. Abre el notebook y selecciona el kernel `.venv` (arriba a la derecha).
4. Pulsa **Run All**.

### Opción 4 · Google Colab (sin instalar nada)

1. Entra a [Google Colab](https://colab.research.google.com/) → *Archivo → Abrir
   cuaderno → GitHub* y pega la URL del repositorio, o usa este enlace directo:
   [abrir Fase 1 en Colab](https://colab.research.google.com/github/Leoces95/entregable-bi-analisis-datos-2026-2-/blob/main/fase_1_comprension_problema/1_comprension_problema.ipynb).
2. En el panel de archivos (ícono de carpeta, a la izquierda) sube `train.csv`.
3. Ejecuta todas las celdas (*Entorno de ejecución → Ejecutar todas*).

Colab ya trae `pandas`, así que no hay que instalar nada más.
