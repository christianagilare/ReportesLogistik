import pandas as pd
import logging
from typing import Any
from config import Config
from .client import AzureDevOpsClient
import os

logger = logging.getLogger(__name__)

def normalize_assigned_to(assigned_to: Any) -> str:
    if not assigned_to:
        return ""
    if isinstance(assigned_to, dict):
        display_name = assigned_to.get("displayName", "")
        unique_name = assigned_to.get("uniqueName", "")
        if display_name and unique_name:
            return f"{display_name} <{unique_name}>"
        return display_name or unique_name
    return str(assigned_to)

def format_date_us(dt) -> str:
    if pd.isna(dt):
        return ""
    time_part = dt.strftime('%I:%M:%S %p')
    if time_part.startswith("0"):
        time_part = time_part[1:]
    return f"{dt.month}/{dt.day}/{dt.year} {time_part}"

def run_azure_devops_export():
    logger.info("Iniciando exportacion de Azure DevOps...")
    
    client = AzureDevOpsClient(
        token=Config.ADO_TOKEN,
        base_url=Config.ADO_BASE_URL,
        org=Config.ADO_ORG,
        project_id=Config.ADO_PROJECT_ID
    )
    
    try:
        wiql_url = client.get_query_wiql_url(Config.ADO_QUERY_ID)
        logger.info("WIQL URL obtenida exitosamente desde metadata.")
    except Exception as e:
        logger.error(f"Fallo al obtener WIQL metadata: {e}")
        return
        
    try:
        work_item_ids = client.execute_wiql(wiql_url)
        logger.info(f"Se encontraron {len(work_item_ids)} work items en el query.")
    except Exception as e:
        logger.error(f"Fallo al ejecutar WIQL: {e}")
        return
        
    if not work_item_ids:
        logger.warning("No hay work items para procesar.")
        return
        
    fields = [
        "System.Id",
        "System.State",
        "System.AssignedTo",
        "Microsoft.VSTS.Scheduling.CompletedWork",
        "System.TeamProject",
        "System.WorkItemType",
        "System.IterationPath",
        "System.Title",
        "System.CreatedDate",
        "Microsoft.VSTS.Common.ClosedDate",
        "System.ChangedDate"
    ]
    
    all_items = []
    chunk_size = 200
    
    for i in range(0, len(work_item_ids), chunk_size):
        chunk = work_item_ids[i:i + chunk_size]
        logger.info(f"Procesando chunk de work items ({i+1} a {min(i+chunk_size, len(work_item_ids))})...")
        
        try:
            items_data = client.get_work_items_batch(chunk, fields)
            all_items.extend(items_data)
        except Exception as e:
            logger.error(f"Fallo al obtener batch de work items (IDs {chunk[0]} a {chunk[-1]}): {e}")
            continue
            
    if not all_items:
        logger.warning("No se pudieron obtener detalles de ningun work item.")
        return
        
    # Transform data for pandas
    flat_data = []
    for item in all_items:
        fields_dict = item.get("fields", {})
        flat_item = {
            "ID": fields_dict.get("System.Id"),
            "State": fields_dict.get("System.State"),
            "Assigned To": normalize_assigned_to(fields_dict.get("System.AssignedTo")),
            "Completed Work": fields_dict.get("Microsoft.VSTS.Scheduling.CompletedWork"),
            "Team Project": fields_dict.get("System.TeamProject"),
            "Work Item Type": fields_dict.get("System.WorkItemType"),
            "Iteration Path": fields_dict.get("System.IterationPath"),
            "Title": fields_dict.get("System.Title"),
            "Created Date": fields_dict.get("System.CreatedDate"),
            "Closed Date": fields_dict.get("Microsoft.VSTS.Common.ClosedDate"),
            "Changed Date": fields_dict.get("System.ChangedDate"),
        }
        flat_data.append(flat_item)
        
    df = pd.DataFrame(flat_data)
    
    # Format dates
    date_columns = ["Created Date", "Closed Date", "Changed Date"]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')
        df[col] = df[col].apply(format_date_us)
        
    # asegurar que exista la carpeta
    import datetime
    dt = datetime.datetime.strptime(Config.TT_DATE_FROM, "%Y-%m-%d")
    month_dir = dt.strftime("%B").upper()
    output_dir = f"{month_dir}/ANEXOS"
    os.makedirs(output_dir, exist_ok=True)

    date_suffix = f"{Config.TT_DATE_FROM.replace('-', '')}_{Config.TT_DATE_TO.replace('-', '')}"
    output_path = f"{output_dir}/azure_devops_unified_{date_suffix}.csv"
    df.to_csv(output_path, index=False)

    logger.info(f"Exportacion de Azure DevOps finalizada. Archivo: {output_path}")

