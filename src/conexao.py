"""
src/conexao.py
Conexão com Google Sheets e operações nas planilhas do projeto ITS.
"""

from datetime import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path


# ============================================================
# Configuração
# ============================================================

BASE_DIR = Path(__file__).parent.parent
CRED_PATH = BASE_DIR / "cred.json"

ESCOPO = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ============================================================
# Planilhas do projeto
# ============================================================

PLANILHAS = {
    "multiplication": {
        "nome": "Multiplication_Report",
        "folder_id": "1Lk_vg5-QgDVL7ScSqLQxpHxS1VCLM5Er",
        "aba_dados": "dadosOriginais",
        "aba_mapeamento": "mapeamento",
        "header_row": 0,
        "label": "Multiplication Report",
    },
    "sales": {
        "nome": "Sales_Report",
        "spreadsheet_id": "1sP900gRFdZReAHRQgej3s3MnElblQZNMWdN8hN4oQoE",
        "aba_dados": "dadosOriginais",
        "aba_mapeamento": "mapeamento",
        "header_row": 1,
        "label": "Sales Report",
    },
}

# Planilha de usuários (autenticação)
USUARIOS_PLANILHA_ID = "1Z_WBSfgiLZ_Qv0-FvCMoKFEt6CfGnIqAV7kleLH-jLo"
ABA_USUARIOS = "usuarios"
ABA_LOGS = "logs"

# Aba auxiliar — classificação de áreas (cooperante/próprio)
ABA_IS_COOPERANTE = "isCooperante"

# Colunas da aba isCooperante (na ordem em que serão gravadas)
COLUNAS_IS_COOPERANTE = [
    "desc_razao_social_filial",
    "cod_cnpj_filial",
    "desc_nome_cooperante",
    "cod_cpf_cnpj_cooperante",
    "cat_is_cooperante",
    "dt_atualizacao",
    "desc_usuario_classificou",
]


# ============================================================
# Conexão
# ============================================================
def conectar_cliente():
    """
    Retorna o cliente gspread autenticado.

    Estratégia (nesta ordem):
    1. Tenta ler de st.secrets["gcp_service_account"] (Streamlit Cloud)
    2. Cai pro arquivo cred.json local (desenvolvimento)
    """
    creds = None

    # === 1. Tenta st.secrets (Streamlit Cloud) ===
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ESCOPO)
    except Exception:
        pass

    # === 2. Fallback para cred.json local ===
    if creds is None:
        if not CRED_PATH.exists():
            raise FileNotFoundError(
                f"Credenciais não encontradas. "
                f"Configure st.secrets['gcp_service_account'] ou crie o arquivo {CRED_PATH}"
            )
        creds = ServiceAccountCredentials.from_json_keyfile_name(str(CRED_PATH), ESCOPO)

    return gspread.authorize(creds)


def abrir_planilha(tipo: str):
    """Abre a planilha pelo tipo ('multiplication' ou 'sales')."""
    if tipo not in PLANILHAS:
        raise ValueError(f"Tipo de planilha inválido: {tipo}")

    config = PLANILHAS[tipo]
    client = conectar_cliente()

    if "spreadsheet_id" in config:
        return client.open_by_key(config["spreadsheet_id"])

    nome = config["nome"]
    arquivos = client.list_spreadsheet_files()
    for arq in arquivos:
        if arq["name"] == nome:
            return client.open_by_key(arq["id"])

    raise FileNotFoundError(
        f"Planilha '{nome}' não encontrada. "
        f"Verifique se a conta de serviço tem acesso a ela."
    )


# ============================================================
# Funções de leitura
# ============================================================
def listar_relatorios() -> list:
    """Retorna lista de tuplas (tipo, label) para uso nas abas."""
    return [(tipo, config["label"]) for tipo, config in PLANILHAS.items()]


def get_header_row(tipo: str) -> int:
    return PLANILHAS[tipo]["header_row"]


def carregar_mapeamento(tipo: str) -> pd.DataFrame:
    """Carrega o DePara da aba 'mapeamento'."""
    config = PLANILHAS[tipo]
    planilha = abrir_planilha(tipo)
    aba = planilha.worksheet(config["aba_mapeamento"])
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)
    return df


def carregar_dados(tipo: str) -> pd.DataFrame:
    """Carrega os dados da aba 'dadosOriginais'."""
    config = PLANILHAS[tipo]
    planilha = abrir_planilha(tipo)
    aba = planilha.worksheet(config["aba_dados"])

    valores = aba.get_all_values()
    if not valores or len(valores) < 2:
        return pd.DataFrame()

    cabecalho = valores[0]
    linhas = valores[1:]
    df = pd.DataFrame(linhas, columns=cabecalho)
    df = df.dropna(axis=1, how="all")
    df = df[df.iloc[:, 0].astype(str).str.strip() != ""]
    return df


# ============================================================
# Funções de escrita (substituir dados)
# ============================================================
def substituir_dados(df: pd.DataFrame, tipo: str) -> int:
    """Apaga todos os dados da aba 'dadosOriginais' e grava o novo DataFrame."""
    config = PLANILHAS[tipo]
    planilha = abrir_planilha(tipo)
    aba = planilha.worksheet(config["aba_dados"])

    aba.clear()

    # === Trata NaN/None ANTES de converter para string ===
    # Substitui todos os tipos de "nada" por string vazia
    import numpy as np
    df_limpo = df.copy()
    df_limpo = df_limpo.replace([np.nan, np.inf, -np.inf, pd.NA, pd.NaT], "")
    df_limpo = df_limpo.fillna("")

    cabecalho = list(df_limpo.columns)

    # Converte cada célula para string segura
    def celula_segura(v):
        if v is None:
            return ""
        if isinstance(v, float):
            if pd.isna(v) or v != v:  # NaN
                return ""
            if v == int(v):
                return str(int(v))  # remove .0 desnecessário
            return str(v)
        if pd.isna(v):
            return ""
        s = str(v).strip()
        if s.lower() in ("nan", "nat", "none"):
            return ""
        return s

    linhas_limpa = [
        [celula_segura(v) for v in row]
        for row in df_limpo.values
    ]

    aba.update([cabecalho] + linhas_limpa, value_input_option="USER_ENTERED")
    return len(df)


# ============================================================
# Funções para a aba isCooperante (Multiplication_Report)
# ============================================================
def garantir_aba_is_cooperante():
    """
    Cria a aba isCooperante na planilha Multiplication_Report se não existir.
    Estrutura (7 colunas):
        - desc_razao_social_filial
        - cod_cnpj_filial
        - desc_nome_cooperante
        - cod_cpf_cnpj_cooperante
        - cat_is_cooperante
        - dt_atualizacao
        - desc_usuario_classificou
    """
    planilha = abrir_planilha("multiplication")
    try:
        aba = planilha.worksheet(ABA_IS_COOPERANTE)
        return aba
    except Exception:
        aba = planilha.add_worksheet(
            title=ABA_IS_COOPERANTE,
            rows=1000,
            cols=len(COLUNAS_IS_COOPERANTE),
        )
        aba.update(
            [COLUNAS_IS_COOPERANTE],
            value_input_option="USER_ENTERED",
        )
        return aba


def carregar_is_cooperante() -> pd.DataFrame:
    """Carrega a aba isCooperante como DataFrame."""
    aba = garantir_aba_is_cooperante()
    valores = aba.get_all_values()

    if not valores or len(valores) < 2:
        return pd.DataFrame(columns=COLUNAS_IS_COOPERANTE)

    cabecalho = valores[0]
    linhas = valores[1:]
    df = pd.DataFrame(linhas, columns=cabecalho)
    df = df[df["desc_razao_social_filial"].astype(str).str.strip() != ""]

    # Garante que todas as colunas existem (caso a aba esteja antiga)
    for col in COLUNAS_IS_COOPERANTE:
        if col not in df.columns:
            df[col] = ""

    return df[COLUNAS_IS_COOPERANTE]


def salvar_is_cooperante(df: pd.DataFrame):
    """Salva o DataFrame completo na aba isCooperante (substitui tudo)."""
    aba = garantir_aba_is_cooperante()
    aba.clear()

    linhas = [COLUNAS_IS_COOPERANTE]

    for _, row in df.iterrows():
        linhas.append([str(row.get(col, "")) for col in COLUNAS_IS_COOPERANTE])

    aba.update(linhas, value_input_option="USER_ENTERED")
    return len(df)


def sincronizar_pares_cooperante(df_dados: pd.DataFrame, email_usuario: str = "") -> tuple:
    """
    Extrai pares únicos (filial + cooperante) do upload e adiciona
    só os NOVOS na aba isCooperante.

    Pré-marca como 'nao' quando o CNPJ da filial = CNPJ do cooperante
    (caso óbvio: área própria).

    Retorna (qtd_novos_total, qtd_aguardando_classificacao)
    """
    col_filial = "desc_razao_social_filial"
    col_coop = "desc_nome_cooperante"
    col_cnpj_filial = "cod_cnpj_filial"
    col_cnpj_coop = "cod_cpf_cnpj_cooperante"

    cols_necessarias = [col_filial, col_coop, col_cnpj_filial, col_cnpj_coop]
    faltando = [c for c in cols_necessarias if c not in df_dados.columns]
    if faltando:
        raise ValueError(f"Colunas faltando para sincronizar isCooperante: {faltando}")

    # Pares únicos do upload
    pares_upload = (
        df_dados[[col_filial, col_coop, col_cnpj_filial, col_cnpj_coop]]
        .drop_duplicates(subset=[col_filial, col_coop])
        .copy()
    )
    pares_upload[col_filial] = pares_upload[col_filial].astype(str).str.strip()
    pares_upload[col_coop] = pares_upload[col_coop].astype(str).str.strip()
    pares_upload[col_cnpj_filial] = pares_upload[col_cnpj_filial].astype(str).str.strip()
    pares_upload[col_cnpj_coop] = pares_upload[col_cnpj_coop].astype(str).str.strip()

    # Carrega o que já existe
    df_existente = carregar_is_cooperante()

    # Set de chaves já existentes para diff rápido
    if not df_existente.empty:
        chaves_existentes = set(
            (str(r).strip(), str(c).strip())
            for r, c in zip(df_existente[col_filial], df_existente[col_coop])
        )
    else:
        chaves_existentes = set()

    # Filtra só pares novos
    novos = pares_upload[
        ~pares_upload.apply(
            lambda r: (r[col_filial], r[col_coop]) in chaves_existentes,
            axis=1,
        )
    ].copy()

    if novos.empty:
        if df_existente.empty:
            return 0, 0
        aguardando = (
            df_existente["cat_is_cooperante"].astype(str).str.strip().isin(["", "—"])
        ).sum()
        return 0, int(aguardando)

    # Pré-classificação: CNPJs iguais -> 'nao' (área própria), senão vazio
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def pre_classificar(row):
        if row[col_cnpj_filial] == row[col_cnpj_coop] and row[col_cnpj_filial] != "":
            return "nao", agora, "[automático]"
        return "", "", ""

    classificacoes = novos.apply(pre_classificar, axis=1, result_type="expand")
    novos["cat_is_cooperante"] = classificacoes[0]
    novos["dt_atualizacao"] = classificacoes[1]
    novos["desc_usuario_classificou"] = classificacoes[2]

    # Mantém só as colunas finais na ordem certa
    novos_final = novos[COLUNAS_IS_COOPERANTE]

    # Concatena com o existente e salva
    df_final = pd.concat([df_existente, novos_final], ignore_index=True)
    salvar_is_cooperante(df_final)

    # Conta aguardando classificação
    aguardando = (
        df_final["cat_is_cooperante"].astype(str).str.strip().isin(["", "—"])
    ).sum()

    return len(novos), int(aguardando)
