# Generador de Informes Automatizados (TrackingTime & Azure DevOps)

Este programa automatiza la extracción, procesamiento y unificación de datos provenientes de TrackingTime y Azure DevOps para generar un informe final en formato Excel.

## Instrucciones y Consideraciones Importantes

### 1. Configuración de Rango de Fechas
*   **TrackingTime**: acota la extracción con `TT_DATE_FROM` y `TT_DATE_TO` en el archivo `.env`.
*   **Azure DevOps (modo por defecto `wiql_env`)**: las fechas **también salen solo del `.env`** (`TT_DATE_FROM` / `TT_DATE_TO`). El programa descarga el WIQL del query guardado (`ADO_QUERY_ID`), reemplaza únicamente los literales de `[System.ChangedDate] >=` y `<=`, y ejecuta ese WIQL. El query de Azure sigue definiendo el resto de filtros (tipo de work item, exclusiones de asignados, etc.), pero **no** el rango de fechas.
*   **Azure DevOps (modo legado `saved_query`)**: usa el query guardado tal cual está en Azure DevOps, incluidas las fechas embebidas. Si eliges este modo, el rango de fechas del informe debe coincidir con el query en Azure.

Modo de ejecución (seleccionable):

| Modo | Cómo se elige | Fechas |
| --- | --- | --- |
| `wiql_env` (default) | `ADO_EXPORT_MODE=wiql_env` o `--ado-export-mode wiql_env` | `.env` (`TT_DATE_FROM` / `TT_DATE_TO`) |
| `saved_query` | `ADO_EXPORT_MODE=saved_query` o `--ado-export-mode saved_query` | Las del query guardado en Azure |

Si se pasan ambos, el flag CLI tiene prioridad sobre `ADO_EXPORT_MODE`.

### 2. Actualización de Proyectos y Personal
Si se desea modificar, añadir nuevas personas o registrar nuevos proyectos en los reportes, es **estrictamente necesario** modificar los archivos correspondientes ubicados en la carpeta `Documentos` (por ejemplo, `CodigosProyectos.csv` y `Equipo.csv`). El programa se basa en estos archivos como referencia para cruzar y validar la información.

### 3. Autenticación, Tokens y Credenciales
Todas las credenciales necesarias deben estar en el archivo `.env`. Se deben tener en cuenta las siguientes consideraciones sobre los accesos:
*   **Tokens de Azure (PAT)**: Los *Personal Access Tokens* de Azure DevOps **tienen fecha de vencimiento**. Si el programa falla al intentar conectarse o descargar datos de Azure, verifica la vigencia del token. Si ha expirado, debes generar uno nuevo en tu cuenta de Azure y reemplazar el valor correspondiente en el archivo `.env`.
*   **Contraseña de TrackingTime**: La integración con TrackingTime no utiliza la contraseña habitual de tu cuenta registrada, sino que utiliza una **contraseña de aplicación** (*App Password*), que debes generar desde la plataforma e incluir en el archivo `.env`.

## Ejecución del Programa
1. Asegúrate de tener las dependencias instaladas (`pip install -r requirements.txt`).
2. Verifica que tu archivo `.env` esté debidamente configurado.
3. Ejecuta el script principal (usa `wiql_env` por defecto): `python main.py`
4. Para forzar el flujo legado del query guardado: `python main.py --ado-export-mode saved_query`
5. El reporte generado se guardará en `Informes/{año}/{mes}/` (por ejemplo, `Informes/2026/07-JULY/`).

### Comparar ambos modos
Para verificar que `wiql_env` y `saved_query` devuelven los **mismos work items** (útil cuando `TT_DATE_FROM` / `TT_DATE_TO` coinciden con las fechas actualmente guardadas en el query de Azure):

```bash
# Alinea las fechas del .env con el query de Azure, por ejemplo:
# TT_DATE_FROM=2026-07-16
# TT_DATE_TO=2026-08-15
python main.py --compare-modes
# equivalente:
python -m azure_devops.compare_modes
```

El comando imprime el conteo de IDs de cada modo, si los conjuntos son iguales y cualquier diferencia. Código de salida `0` si coinciden, `1` si no. No genera el Excel.

Tests unitarios de la reescritura WIQL (no requieren credenciales de Azure):

```bash
python -m unittest discover -s tests -v
```
