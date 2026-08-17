import math
import pandas as pd
import logging

logger = logging.getLogger(__name__)

MIN_PERCENT = 1
TOTAL_PERCENT = 100


def _allocate_percentages(raw_fractions: list[float]) -> list[float]:
    """
    Asigna porcentajes enteros (1-100) que suman exactamente 100 por persona.
    - Valores > 0 con parte entera 0 reciben minimo 1%.
    - El resto se distribuye por mayor resto (metodo Hamilton).
    Retorna decimales (0.34 = 34%).
    """
    n = len(raw_fractions)
    if n == 0:
        return []
    if n == 1:
        return [1.0]

    total_raw = sum(raw_fractions)
    if total_raw <= 0:
        return [0.0] * n

    normalized = [f / total_raw for f in raw_fractions]
    scaled = [f * TOTAL_PERCENT for f in normalized]

    floors = [math.floor(x) for x in scaled]
    remainders = [s - math.floor(s) for s in scaled]

    for i, (raw, fl) in enumerate(zip(raw_fractions, floors)):
        if raw > 0 and fl == 0:
            floors[i] = MIN_PERCENT

    deficit = TOTAL_PERCENT - sum(floors)

    if deficit > 0:
        order = sorted(range(n), key=lambda i: remainders[i], reverse=True)
        for k in range(deficit):
            floors[order[k % n]] += 1
    elif deficit < 0:
        order = sorted(range(n), key=lambda i: (floors[i], remainders[i]), reverse=True)
        remaining = -deficit
        attempts = 0
        while remaining > 0 and attempts < n * abs(deficit) + n:
            idx = order[attempts % n]
            min_allowed = MIN_PERCENT if raw_fractions[idx] > 0 else 0
            if floors[idx] > min_allowed:
                floors[idx] -= 1
                remaining -= 1
            attempts += 1

    return [round(f / TOTAL_PERCENT, 2) for f in floors]


def _distribute_equal_percentages(n_projects: int, person_index: int = 0) -> list[float]:
    """Distribuye 100% en enteros lo mas equitativamente posible entre n proyectos."""
    if n_projects == 0:
        return []
    if n_projects == 1:
        return [1.0]

    base = TOTAL_PERCENT // n_projects
    remainder = TOTAL_PERCENT % n_projects
    pcts = [base] * n_projects

    for i in range(remainder):
        idx = (person_index + i) % n_projects
        pcts[idx] += 1

    return [round(p / TOTAL_PERCENT, 2) for p in pcts]


def add_new_collaborators(presentacion: pd.DataFrame, collaborators: list[dict]) -> pd.DataFrame:
    """
    Agrega registros para colaboradores nuevos en todos los proyectos existentes.
    No modifica registros existentes. Omite colaboradores que ya estan en la tabla.
    """
    if not collaborators:
        return presentacion

    projects = presentacion[["PROYECTO", "CODIGO"]].drop_duplicates().reset_index(drop=True)
    n_projects = len(projects)
    if n_projects == 0:
        logger.warning("No hay proyectos en la tabla para asignar nuevos colaboradores.")
        return presentacion

    existing_names = set(presentacion["NOMBRE"].dropna().unique())
    new_rows = []
    added_people = 0

    for person_index, collab in enumerate(collaborators):
        nombre = collab["nombre"]
        if nombre in existing_names:
            logger.info("Colaborador '%s' ya existe en la tabla, se omite.", nombre)
            continue

        pcts = _distribute_equal_percentages(n_projects, person_index)
        for i, proj in projects.iterrows():
            new_rows.append({
                "EMPRESA": collab["empresa"],
                "NOMBRE": nombre,
                "CÉDULA DE IDENTIDAD": collab["cedula"],
                "PROYECTO": proj["PROYECTO"],
                "CODIGO": proj["CODIGO"],
                "% ASIGNADO A PROYECTOS": pcts[i],
            })

        existing_names.add(nombre)
        added_people += 1

    if not new_rows:
        return presentacion

    logger.info(
        "Se agregaron %s registros para %s colaborador(es) nuevo(s).",
        len(new_rows),
        added_people,
    )
    result = pd.concat([presentacion, pd.DataFrame(new_rows)], ignore_index=True)
    result["CÉDULA DE IDENTIDAD"] = pd.to_numeric(
        result["CÉDULA DE IDENTIDAD"], errors="coerce"
    ).astype("int64")
    return result

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

    presentacion = pd.concat([horas_az, horas_tr], ignore_index=True)

    presentacion = presentacion.merge(
        total_horas_combinado[["Usuario", "Total_Horas"]],
        left_on="NOMBRE",
        right_on="Usuario",
        how="left"
    ).drop(columns=["Usuario"])

    # Excluir filas sin horas registradas
    presentacion = presentacion[presentacion["Suma"] > 0].copy()

    presentacion["% ASIGNADO A PROYECTOS"] = 0.0
    for _, group in presentacion.groupby("NOMBRE", sort=False):
        total_horas = group["Total_Horas"].iloc[0]
        if pd.isna(total_horas) or total_horas <= 0:
            continue

        raw_fractions = (group["Suma"] / total_horas).tolist()
        presentacion.loc[group.index, "% ASIGNADO A PROYECTOS"] = _allocate_percentages(raw_fractions)

    presentacion.drop(columns=["Total_Horas"], inplace=True)
    presentacion.drop(columns=["Suma", "Origen"], inplace=True, errors="ignore")

    return presentacion
