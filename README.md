# Generador de Informes Automatizados (TrackingTime & Azure DevOps)

Este programa automatiza la extracción, procesamiento y unificación de datos provenientes de TrackingTime y Azure DevOps para generar un informe final en formato Excel.

## Instrucciones y Consideraciones Importantes

### 1. Configuración de Rango de Fechas
*   **Azure DevOps**: El rango de fechas del informe, así como otras exclusiones o filtros específicos del *query*, deben configurarse directamente en la plataforma de Azure DevOps.
*   **TrackingTime**: Para que la extracción de TrackingTime acote correctamente la información, debes **setear la fecha de inicio y fin en el archivo `.env`**.

### 2. Actualización de Proyectos y Personal
Si se desea modificar, añadir nuevas personas o registrar nuevos proyectos en los reportes, es **estrictamente necesario** modificar los archivos correspondientes ubicados en la carpeta `Documentos` (por ejemplo, `CodigosProyectos.csv` y `Equipo.csv`). El programa se basa en estos archivos como referencia para cruzar y validar la información.

### 3. Autenticación, Tokens y Credenciales
Todas las credenciales necesarias deben estar en el archivo `.env`. Se deben tener en cuenta las siguientes consideraciones sobre los accesos:
*   **Tokens de Azure (PAT)**: Los *Personal Access Tokens* de Azure DevOps **tienen fecha de vencimiento**. Si el programa falla al intentar conectarse o descargar datos de Azure, verifica la vigencia del token. Si ha expirado, debes generar uno nuevo en tu cuenta de Azure y reemplazar el valor correspondiente en el archivo `.env`.
*   **Contraseña de TrackingTime**: La integración con TrackingTime no utiliza la contraseña habitual de tu cuenta registrada, sino que utiliza una **contraseña de aplicación** (*App Password*), que debes generar desde la plataforma e incluir en el archivo `.env`.

## Ejecución del Programa
1. Asegúrate de tener las dependencias instaladas (`pip install -r requirements.txt`).
2. Verifica que tu archivo `.env` esté debidamente configurado.
3. Ejecuta el script principal: `python main.py`
4. El reporte generado se guardará en la carpeta `output`.
