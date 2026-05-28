"""
config/theme.py
CSS e helpers de tema compartilhados entre todas as páginas.
"""

import base64
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent.parent


def aplicar_tema():
    """Aplica o CSS global do app. Chamar no início de cada página."""
    st.markdown("""
<style>
:root {
    --green-primary:  #27AE60;
    --green-dark:     #1E8449;
    --green-light:    #E9F7EF;
    --green-mid:      #A9DFBF;
    --text-primary:   #1A1A1A;
    --text-secondary: #6B7280;
    --bg-main:        #F8FAF9;
    --bg-white:       #FFFFFF;
    --border:         #E5E7EB;
    --shadow:         0 1px 4px rgba(0,0,0,0.07);
}

html, body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
}

[class*="css"]:not([class*="ag-"]) {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--bg-white) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

[data-testid="stSidebarNav"] { padding-top: 1.5rem !important; }
[data-testid="stSidebarNav"] a {
    padding: 9px 16px !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    transition: background 0.15s !important;
    color: var(--text-primary) !important;
    text-decoration: none !important;
    display: flex !important;
    align-items: center !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: var(--green-light) !important;
    color: var(--green-dark) !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: var(--green-light) !important;
    color: var(--green-dark) !important;
    font-weight: 600 !important;
}
[data-testid="stSidebarNav"]::before { display: none !important; }

/* ── Header com logo ── */
.its-header {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    padding: 0.5rem 0 1.2rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
}
.its-header img {
    height: 80px;
    width: auto;
}
.its-header-divider {
    width: 1px;
    height: 48px;
    background: var(--border);
}
.its-header-text h1 {
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
    line-height: 1.2 !important;
}
.its-header-text p {
    font-size: 14px !important;
    color: var(--text-secondary) !important;
    margin: 4px 0 0 !important;
}

/* ── Conteúdo principal ── */
.main .block-container {
    padding: 1.5rem 2.5rem 2rem !important;
    max-width: 1400px !important;
}

/* ── Títulos ── */
h1 { font-size: 1.9rem !important; font-weight: 700 !important; }
h2 { font-size: 1.5rem !important; font-weight: 600 !important; }
h3 { font-size: 1.2rem !important; font-weight: 600 !important; }

/* ── Botão primário ── */
.stButton > button[kind="primary"] {
    background-color: var(--green-primary) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 0.5rem 1.2rem !important;
    transition: background 0.2s !important;
}
.stButton > button[kind="primary"]:hover { background-color: var(--green-dark) !important; }

/* ── Botão secundário ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    border: 1px solid var(--border) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    border-color: var(--green-primary) !important;
    color: var(--green-primary) !important;
}

/* ── Métricas ── */
[data-testid="stMetric"] {
    background: var(--bg-white) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 1rem 1.2rem !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="stMetricLabel"] { color: var(--text-secondary) !important; font-size: 13px !important; }
[data-testid="stMetricValue"] { color: var(--text-primary) !important; font-size: 1.6rem !important; font-weight: 700 !important; }

/* ── Alerts, dataframe, expander ── */
.stAlert { border-radius: 8px !important; font-size: 14px !important; }

[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* Cabeçalho da tabela (st.dataframe) em preto e negrito */
[data-testid="stDataFrame"] thead th,
[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stDataFrameResizable"] thead th,
[data-testid="stDataFrameResizable"] [role="columnheader"] {
    background-color: #F8FAF9 !important;
    color: #1A1A1A !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}
/* Garante que o conteúdo dentro do header (span/div) também fique preto e bold */
[data-testid="stDataFrame"] thead th *,
[data-testid="stDataFrame"] [role="columnheader"] *,
[data-testid="stDataFrameResizable"] thead th *,
[data-testid="stDataFrameResizable"] [role="columnheader"] * {
    color: #1A1A1A !important;
    font-weight: 700 !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    background: var(--bg-white) !important;
}

hr { border-color: var(--border) !important; }

/* ── Botões primários (verde em vez do azul padrão do Streamlit) ── */
div[data-testid="stForm"] button[kind="primaryFormSubmit"],
div[data-testid="stForm"] button[kind="primary"],
.stButton > button[kind="primary"],
button[kind="primary"] {
    background-color: var(--green-primary) !important;
    border-color: var(--green-primary) !important;
    color: #FFFFFF !important;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
div[data-testid="stForm"] button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover,
button[kind="primary"]:hover {
    background-color: var(--green-dark) !important;
    border-color: var(--green-dark) !important;
}

/* ── Abas (st.tabs) com destaque verde ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-secondary) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: var(--green-dark) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--green-primary) !important;
}
.stTabs [data-baseweb="tab-border"] {
    background-color: var(--border) !important;
}

/* ── Radio button (papel admin/usuario) ── */
/* Aro externo do radio selecionado */
.stRadio [role="radiogroup"] label[data-baseweb="radio"] div[aria-checked="true"] {
    background-color: var(--green-primary) !important;
    border-color: var(--green-primary) !important;
}
/* Bolinha interna APENAS do radio selecionado */
.stRadio [role="radiogroup"] label[data-baseweb="radio"] div[aria-checked="true"] > div {
    background-color: #FFFFFF !important;
}
/* Garante que NÃO selecionado fica em branco/cinza */
.stRadio [role="radiogroup"] label[data-baseweb="radio"] div[aria-checked="false"] {
    background-color: #FFFFFF !important;
    border-color: #D1D5DB !important;
}
.stRadio [role="radiogroup"] label[data-baseweb="radio"] div[aria-checked="false"] > div {
    background-color: transparent !important;
}

/* ── Checkbox marcado ── */
.stCheckbox [role="checkbox"][aria-checked="true"] {
    background-color: var(--green-primary) !important;
    border-color: var(--green-primary) !important;
}

/* ── Links (ex: 'Browse files' do file_uploader) ── */
.stFileUploader a,
[data-testid="stFileUploader"] a,
[data-testid="stFileUploader"] button {
    color: var(--green-dark) !important;
}
[data-testid="stFileUploader"] section {
    border-color: var(--border) !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: var(--green-primary) !important;
}

/* ── Spinner ── */
.stSpinner > div > div {
    border-top-color: var(--green-primary) !important;
}

/* ── Focus dos inputs (linha azul ao clicar) ── */
input:focus,
textarea:focus,
[data-baseweb="input"]:focus-within,
[data-baseweb="select"]:focus-within {
    border-color: var(--green-primary) !important;
    box-shadow: 0 0 0 2px rgba(39, 174, 96, 0.15) !important;
}

/* ── Selectbox ao abrir (highlight do item) ── */
[data-baseweb="menu"] [aria-selected="true"] {
    background-color: var(--green-light) !important;
    color: var(--green-dark) !important;
}

/* ── Slider e progress ── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background-color: var(--green-primary) !important;
}
.stProgress > div > div > div > div {
    background-color: var(--green-primary) !important;
}

/* ── Cards para a Home (estilo painel Stine) ── */
.its-card {
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.3rem 1.4rem;
    box-shadow: var(--shadow);
    transition: all 0.2s;
    height: 100%;
    min-height: 180px;
    display: flex;
    flex-direction: column;
}
.its-card:hover {
    border-color: var(--green-primary);
    box-shadow: 0 4px 12px rgba(39,174,96,0.12);
}
.its-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 4px;
}
.its-card-subtitle {
    font-size: 13px;
    color: var(--text-secondary);
    margin: 0 0 10px;
}
.its-card-desc {
    font-size: 13.5px;
    color: var(--text-primary);
    line-height: 1.5;
    margin: 0 0 12px;
    flex-grow: 1;
}
.its-tag {
    display: inline-block;
    background: var(--green-light);
    color: var(--green-dark);
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
    margin-right: 5px;
    margin-bottom: 4px;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-main); }
::-webkit-scrollbar-thumb { background: var(--green-mid); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--green-primary); }
</style>
""", unsafe_allow_html=True)


def logo_base64():
    """Procura uma logo em assets/ e retorna como base64."""
    for ext in ["png", "svg", "jpg", "jpeg"]:
        path = BASE_DIR / "assets" / f"logo.{ext}"
        if path.exists():
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            data = base64.b64encode(path.read_bytes()).decode()
            return f"data:{mime};base64,{data}"
    return None


def imagem_base64(nome_arquivo: str):
    """Lê uma imagem qualquer de assets/ e retorna como base64."""
    path = BASE_DIR / "assets" / nome_arquivo
    if not path.exists():
        return None
    ext = path.suffix.lower().lstrip(".")
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def page_header(titulo: str, subtitulo: str = ""):
    """Header padrão de cada página: [Logo] | [Título / subtítulo]"""
    src = logo_base64()
    logo_html = (
        f'<img src="{src}" />'
        if src
        else '<span style="font-size:2.2rem;font-weight:700;color:#27AE60;">🌱</span>'
    )
    sub_html = f'<p>{subtitulo}</p>' if subtitulo else ""

    st.markdown(f"""
<div class="its-header">
    {logo_html}
    <div class="its-header-divider"></div>
    <div class="its-header-text">
        <h1>{titulo}</h1>
        {sub_html}
    </div>
</div>
""", unsafe_allow_html=True)


def secao_titulo(label: str, titulo: str, descricao: str = ""):
    """Bloco editorial: label em caps + título grande + descrição."""
    desc_html = (
        f'<p style="font-size:17px;color:#1A1A1A;margin:6px 0 0;line-height:1.6;font-weight:500;">{descricao}</p>'
        if descricao else ""
    )
    st.markdown(f"""
<div style="margin: 1.5rem 0 1rem;">
    <p style="font-size:16px;font-weight:700;color:#1A1A1A;text-transform:uppercase;
              letter-spacing:0.05em;margin:0 0 6px;">{label}</p>
    <h2 style="font-size:1.9rem;font-weight:700;color:#1A1A1A;margin:0;line-height:1.2;">{titulo}</h2>
    {desc_html}
</div>
""", unsafe_allow_html=True)
