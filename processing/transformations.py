import pandas as pd
import logging

logger = logging.getLogger(__name__)

# FASE 2-A: TRANSFORMACION DEL DATA SOURCE AZURE DEVOPS
def transform_azure_devops(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando datos de Azure DevOps...")
    
    # Limpiar campo Assigned To -> crear columna Assigned To Clean
    # Extraer todo lo que esta ANTES del caracter "<"
    if "Assigned To" in df.columns:
        df["Assigned To Clean"] = df["Assigned To"].astype(str).str.split("<").str[0]
        
        # Limpiar sufijos de empresa (en este orden exacto):
        df["Assigned To Clean"] = df["Assigned To Clean"].str.replace(" Logiztik Alliance ", "", regex=False)
        df["Assigned To Clean"] = df["Assigned To Clean"].str.replace(" New Data (Externo) ", "", regex=False)
        df["Assigned To Clean"] = df["Assigned To Clean"].str.replace(" New Data ", "", regex=False)
        df["Assigned To Clean"] = df["Assigned To Clean"].str.strip()
        
        # Eliminar la columna original "Assigned To"
        df.drop(columns=["Assigned To"], inplace=True)
    else:
        df["Assigned To Clean"] = ""
        
    # Filtrar filas vacias
    df = df[df["Assigned To Clean"].notna() & (df["Assigned To Clean"] != "")]
    return df

# FASE 2-B: TRANSFORMACION DEL DATA SOURCE TRACKINGTIME
def transform_trackingtime(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Transformando datos de TrackingTime...")
    
    # Eliminar columnas innecesarias: Service y Client.
    if "Service" in df.columns:
        df = df.drop(columns=["Service"])
    if "Client" in df.columns:
        df = df.drop(columns=["Client"])
        
    # Reemplazar proyectos nulos: Project donde sea NaN o vacio -> reemplazar por "Administracion"
    df["Project"] = df["Project"].replace("", "Administración")
    df["Project"] = df["Project"].fillna("Administración")
    
    # Normalizar nombres de proyecto
    replacements = {
        "Controles de Cambio y Errores": "Controles de Cambios y Errores",
        "Integraciones Clientes": "INTEGRACIONES"
    }
    df["Project"] = df["Project"].replace(replacements)
    
    # Filtrar filas vacias en User
    df = df[df["User"].notna() & (df["User"] != "")]
    return df

# FASE 2-C: CONSTRUCCION DE LAS 4 TABLAS DERIVADAS
def build_tables(azure_df, tracking_df, codigos_df, equipo_df):
    logger.info("Construyendo tablas derivadas...")
    
    # TABLA 1: total_horas_usuario_azure
    total_horas_usuario_azure = (
        azure_df
        .groupby("Assigned To Clean", as_index=False)
        .agg(Suma_Horas=("Completed Work", "sum"))
        .rename(columns={"Assigned To Clean": "Usuario"})
    )
    total_horas_usuario_azure = total_horas_usuario_azure[
        total_horas_usuario_azure["Usuario"].notna() & (total_horas_usuario_azure["Usuario"] != "")
    ]
    
    # TABLA 2: total_horas_usuario_tracking
    total_horas_usuario_tracking = (
        tracking_df
        .groupby("User", as_index=False)
        .agg(Suma_Horas=("Hours", "sum"))
        .rename(columns={"User": "Usuario"})
    )
    total_horas_usuario_tracking = total_horas_usuario_tracking[
        total_horas_usuario_tracking["Usuario"].notna() & (total_horas_usuario_tracking["Usuario"] != "")
    ]
    
    # TABLA 3: total_horas_combinado
    combined = pd.concat([total_horas_usuario_azure, total_horas_usuario_tracking], ignore_index=True)
    combined = (
        combined
        .groupby("Usuario", as_index=False)
        .agg(Total_Horas=("Suma_Horas", "sum"))
    )
    # LEFT JOIN con Equipo.csv por: combined["Usuario"] == equipo["Nombre Azure"]
    combined = combined.merge(
        equipo_df[["Nombre Azure", "NOMBRE"]],
        left_on="Usuario",
        right_on="Nombre Azure",
        how="left"
    )
    # La columna final de usuario es "NOMBRE"
    combined = combined[["NOMBRE", "Total_Horas"]].rename(columns={"NOMBRE": "Usuario"})
    
    # TABLA 4: horas_azure
    horas_az = (
        azure_df
        .groupby(["Team Project", "Assigned To Clean"], as_index=False)
        .agg(Suma=("Completed Work", "sum"))
    )
    horas_az = horas_az[horas_az["Assigned To Clean"].notna() & (horas_az["Assigned To Clean"] != "")]
    
    horas_az = horas_az.merge(
        equipo_df[["EMPRESA", "NOMBRE", "Nombre Azure", "CÉDULA DE IDENTIDAD"]],
        left_on="Assigned To Clean",
        right_on="Nombre Azure",
        how="left"
    ).drop(columns=["Nombre Azure"])
    
    horas_az = horas_az.merge(
        codigos_df[["Codigo Proyecto", "Proyecto", "Nombre Azure"]],
        left_on="Team Project",
        right_on="Nombre Azure",
        how="left"
    ).drop(columns=["Nombre Azure", "Team Project", "Assigned To Clean"])
    
    horas_az = horas_az[[
        "EMPRESA", "NOMBRE", "CÉDULA DE IDENTIDAD",
        "Proyecto", "Codigo Proyecto", "Suma"
    ]].rename(columns={
        "NOMBRE": "NOMBRE",
        "Proyecto": "PROYECTO",
        "Codigo Proyecto": "CODIGO"
    })
    horas_az["Origen"] = "Azure"
    
    # TABLA 5: horas_tracking
    horas_tr = (
        tracking_df
        .groupby(["Project", "User"], as_index=False)
        .agg(Suma=("Hours", "sum"))
    )
    horas_tr = horas_tr[horas_tr["User"].notna() & (horas_tr["User"] != "")]
    
    horas_tr = horas_tr.merge(
        equipo_df[["EMPRESA", "NOMBRE", "Nombre Azure", "CÉDULA DE IDENTIDAD"]],
        left_on="User",
        right_on="Nombre Azure",
        how="left"
    ).drop(columns=["Nombre Azure", "User"])
    
    horas_tr = horas_tr.merge(
        codigos_df[["Codigo Proyecto", "Proyecto", "Nombre Tracking"]],
        left_on="Project",
        right_on="Nombre Tracking",
        how="left"
    ).drop(columns=["Nombre Tracking", "Project"])
    
    horas_tr = horas_tr[[
        "EMPRESA", "NOMBRE", "CÉDULA DE IDENTIDAD",
        "Proyecto", "Codigo Proyecto", "Suma"
    ]].rename(columns={
        "Proyecto": "PROYECTO",
        "Codigo Proyecto": "CODIGO"
    })
    horas_tr["Origen"] = "Tracking"
    
    return {
        "total_horas_combinado": combined,
        "horas_azure": horas_az,
        "horas_tracking": horas_tr
    }

# FASE 2-D: TABLA DE PRESENTACION (HOJA PRINCIPAL)
def build_presentation_table(horas_az, horas_tr, total_horas_combinado):
    logger.info("Construyendo tabla de presentacion...")
    
    # Combinar HORAS AZURE + HORAS TRACKING
    presentacion = pd.concat([horas_az, horas_tr], ignore_index=True)
    
    # LEFT JOIN con total_horas_combinado
    presentacion = presentacion.merge(
        total_horas_combinado[["Usuario", "Total_Horas"]],
        left_on="NOMBRE",
        right_on="Usuario",
        how="left"
    ).drop(columns=["Usuario"])
    
    # Calcular % asignado a proyectos
    presentacion["% ASIGNADO A PROYECTOS"] = presentacion.apply(
        lambda row: 0 if (pd.isna(row["Total_Horas"]) or row["Total_Horas"] == 0)
                    else round(row["Suma"] / row["Total_Horas"], 2),
        axis=1
    )
    
    presentacion.drop(columns=["Total_Horas"], inplace=True)
    
    # Comentar / eliminar las columnas Suma y Origen del Excel final sin afectar el calculo previo
    presentacion.drop(columns=["Suma", "Origen"], inplace=True, errors="ignore")
    
    return presentacion
