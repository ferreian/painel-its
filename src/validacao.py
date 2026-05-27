import re
import pandas as pd


def normalizar(texto: str) -> str:
    """
    Normaliza um texto para comparação:
    - Remove espaços do início/fim
    - Substitui múltiplos espaços por um único
    """
    if not isinstance(texto, str):
        return ""
    return re.sub(r"\s+", " ", texto.strip())


def validar_colunas(df_excel: pd.DataFrame, df_mapeamento: pd.DataFrame) -> dict:
    """
    Compara as colunas do Excel com o DePara (normalizando espaços).
    """
    excel_norm = {normalizar(c): c for c in df_excel.columns}
    esperadas_norm = [normalizar(c) for c in df_mapeamento["nome_excel"]]

    faltando = [
        nome_original for nome_original, nome_norm
        in zip(df_mapeamento["nome_excel"], esperadas_norm)
        if nome_norm not in excel_norm
    ]
    extras = [
        excel_norm[k] for k in excel_norm if k not in esperadas_norm
    ]

    fora_de_ordem = []
    if not faltando:
        colunas_excel_norm = [normalizar(c) for c in df_excel.columns]
        ordem_real = [c for c in colunas_excel_norm if c in esperadas_norm]
        for esperada, real in zip(esperadas_norm, ordem_real):
            if esperada != real:
                fora_de_ordem.append({"esperada": esperada, "encontrada": real})

    return {
        "ok": not faltando and not extras and not fora_de_ordem,
        "faltando": faltando,
        "extras": extras,
        "fora_de_ordem": fora_de_ordem,
        "mapa_normalizado": excel_norm,
    }


def aplicar_mapeamento(df_excel: pd.DataFrame, df_mapeamento: pd.DataFrame) -> pd.DataFrame:
    """
    Reordena e renomeia as colunas conforme o DePara.
    """
    excel_norm = {normalizar(c): c for c in df_excel.columns}

    colunas_origem_reais = []
    rename_map = {}
    for _, row in df_mapeamento.iterrows():
        nome_excel = row["nome_excel"]
        nome_destino = row["nome_destino"]
        nome_norm = normalizar(nome_excel)
        nome_real = excel_norm[nome_norm]
        colunas_origem_reais.append(nome_real)
        rename_map[nome_real] = nome_destino

    df_novo = df_excel[colunas_origem_reais].copy()
    df_novo = df_novo.rename(columns=rename_map)
    return df_novo


def converter_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte tipos baseado no prefixo do nome da coluna:
    - dt_  -> data no formato dd/mm/aaaa
    - vl_  -> número decimal (float)
    - qt_  -> número inteiro
    - cat_, desc_, cod_ -> texto
    """
    df = df.copy()

    for col in df.columns:
        if col.startswith("dt_"):
            convertido = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")
            mask_nulo = convertido.isna() & df[col].notna()
            if mask_nulo.any():
                convertido_2 = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                convertido = convertido.fillna(convertido_2)
            df[col] = convertido.dt.strftime("%d/%m/%Y")

        elif col.startswith("vl_"):
            df[col] = (
                df[col].astype(str)
                .str.replace("R$", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

        elif col.startswith("qt_"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        else:
            df[col] = df[col].astype(str).where(df[col].notna(), "")

    return df