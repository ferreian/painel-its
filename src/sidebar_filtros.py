"""
src/sidebar_filtros.py
Helper para criar filtros hierárquicos na sidebar com checkbox + busca.
"""

import streamlit as st
import pandas as pd


# CSS para personalizar o visual dos filtros
CSS_FILTROS = """
<style>
    /* Container da sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FAFAFA;
    }

    /* Headers de seção (▼ Categoria) */
    .filtro-secao-titulo {
        font-size: 17px;
        font-weight: 700;
        color: #1A1A1A;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 1.5rem 0 0.8rem;
        padding-bottom: 6px;
        border-bottom: 2px solid #27AE60;
    }

    /* Label do filtro individual */
    .filtro-label {
        font-size: 15px;
        font-weight: 600;
        color: #1A1A1A;
        margin: 0.8rem 0 0.4rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Indicador de hierarquia (↖) */
    .filtro-hierarquia {
        color: #27AE60;
        font-size: 14px;
        font-weight: 700;
    }

    /* Checkbox compacto */
    section[data-testid="stSidebar"] .stCheckbox {
        margin: 0 !important;
        padding: 3px 0 !important;
    }
    section[data-testid="stSidebar"] .stCheckbox label {
        font-size: 13px !important;
        color: #1A1A1A !important;
    }

    /* Caixa de busca compacta com ícone */
    section[data-testid="stSidebar"] .stTextInput input {
        font-size: 12px !important;
        padding: 4px 8px 4px 28px !important;
        background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%2327AE60' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: 8px center !important;
    }

    /* Container scrollável dos checkboxes */
    .filtro-checklist {
        max-height: 180px;
        overflow-y: auto;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 6px;
        background: #FFFFFF;
        margin-bottom: 0.5rem;
    }
    .filtro-checklist::-webkit-scrollbar {
        width: 6px;
    }
    .filtro-checklist::-webkit-scrollbar-thumb {
        background: #A9DFBF;
        border-radius: 3px;
    }

    /* Botão de limpar filtros */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #FFFFFF !important;
        color: #1A1A1A !important;
        border: 1px solid #E5E7EB !important;
        font-size: 12px !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #E9F7EF !important;
        border-color: #27AE60 !important;
        color: #1E8449 !important;
    }
</style>
"""


def aplicar_css_filtros():
    """Aplica o CSS dos filtros (deve ser chamado uma vez na página)."""
    st.markdown(CSS_FILTROS, unsafe_allow_html=True)


def titulo_secao(texto: str):
    """Renderiza um título de seção da sidebar."""
    st.sidebar.markdown(
        f'<div class="filtro-secao-titulo">{texto}</div>',
        unsafe_allow_html=True,
    )


def filtro_multiselect(
    label: str,
    opcoes: list,
    chave: str,
    depende_de: bool = False,
    threshold_busca: int = 5,
    default: list = None,
) -> list:
    """
    Cria um filtro multiselect com checkboxes + busca opcional.
    Funciona tanto direto na sidebar quanto dentro de um expander.

    Args:
        label: nome do filtro
        opcoes: lista de valores disponíveis
        chave: key única no session_state
        depende_de: True se o filtro depende de outro acima (mostra ↖)
        threshold_busca: a partir de quantos itens mostra a caixa de busca
        default: lista de valores que vêm pré-marcados (apenas na 1ª renderização)

    Returns:
        Lista de valores selecionados (vazia = nenhum filtro)
    """
    # Label com indicador hierárquico
    indicador = '<span class="filtro-hierarquia">↖</span>' if depende_de else ''
    st.markdown(
        f'<div class="filtro-label">{label} {indicador}</div>',
        unsafe_allow_html=True,
    )

    # Remove valores vazios/None e ordena
    opcoes_limpas = sorted([str(o) for o in opcoes if str(o).strip() not in ["", "nan", "None"]])

    if not opcoes_limpas:
        st.caption("Sem opções disponíveis")
        return []

    # Caixa de busca quando tem muitos itens
    busca = ""
    if len(opcoes_limpas) > threshold_busca:
        busca = st.text_input(
            "Buscar",
            key=f"busca_{chave}",
            placeholder="Buscar nomes...",
            label_visibility="collapsed",
        )

    # Filtra opções pela busca
    if busca.strip():
        opcoes_filtradas = [o for o in opcoes_limpas if busca.lower() in o.lower()]
    else:
        opcoes_filtradas = opcoes_limpas

    # === Aplica default na primeira renderização ===
    # Marca uma chave de "ja_inicializou" para não sobrescrever depois
    flag_init = f"init_{chave}"
    if default and flag_init not in st.session_state:
        for valor in opcoes_filtradas:
            key_check = f"check_{chave}_{valor}"
            if valor in default and key_check not in st.session_state:
                st.session_state[key_check] = True
        st.session_state[flag_init] = True

    # Container dos checkboxes
    st.markdown('<div class="filtro-checklist">', unsafe_allow_html=True)

    selecionados = []
    for valor in opcoes_filtradas:
        key_check = f"check_{chave}_{valor}"
        if st.checkbox(valor, key=key_check):
            selecionados.append(valor)

    st.markdown('</div>', unsafe_allow_html=True)

    return selecionados


def botao_limpar():
    """Renderiza o botão de limpar filtros."""
    if st.sidebar.button("🔄 Limpar todos os filtros", use_container_width=True):
        # Remove todas as chaves do session_state que começam com 'check_' ou 'busca_'
        keys_para_remover = [
            k for k in st.session_state.keys()
            if k.startswith("check_") or k.startswith("busca_")
        ]
        for k in keys_para_remover:
            del st.session_state[k]
        st.rerun()


def aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    """
    Aplica os filtros selecionados ao DataFrame.

    Args:
        df: DataFrame original
        filtros: dict {coluna: [valores_selecionados]}

    Returns:
        DataFrame filtrado
    """
    df_filtrado = df.copy()
    for coluna, valores in filtros.items():
        if valores and coluna in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[coluna].astype(str).isin(valores)]
    return df_filtrado
