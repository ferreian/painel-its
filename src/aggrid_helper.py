"""
src/aggrid_helper.py
Helper para padronizar a exibição de tabelas com AgGrid.
Inclui filtros flutuantes E os 3 pontos do menu de coluna.
"""

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from st_aggrid.shared import ColumnsAutoSizeMode


# CSS customizado — mira nos ícones específicos do AgGrid
CUSTOM_CSS = {
    # === Header preto e negrito sobre fundo cinza claro ===
    ".ag-header": {
        "background-color": "#F8FAF9 !important",
        "border-bottom": "2px solid #27AE60 !important",
    },
    ".ag-header-row": {
        "background-color": "#F8FAF9 !important",
    },
    ".ag-header-cell": {
        "background-color": "#F8FAF9 !important",
    },
    ".ag-header-cell-label": {
        "color": "#1A1A1A !important",
        "font-weight": "700",
    },
    ".ag-header-cell-text": {
        "color": "#1A1A1A !important",
        "font-size": "13px !important",
        "font-weight": "700 !important",
    },
    # === Ícones — FORÇA OS 3 PONTOS E O FILTRO ===
    ".ag-icon": {
        "color": "#27AE60 !important",
        "opacity": "1 !important",
    },
    ".ag-header-icon": {
        "color": "#27AE60 !important",
        "opacity": "1 !important",
    },
    # Botão do menu (3 pontos) sempre visível
    ".ag-header-cell-menu-button": {
        "opacity": "1 !important",
        "visibility": "visible !important",
        "display": "flex !important",
    },
    ".ag-header-cell-menu-button span": {
        "color": "#1A1A1A !important",
    },
    # Ícone específico do menu (3 pontos)
    ".ag-icon-menu": {
        "color": "#1A1A1A !important",
        "opacity": "1 !important",
    },
    # Ícone específico do filtro (funil)
    ".ag-icon-filter": {
        "color": "#27AE60 !important",
        "opacity": "1 !important",
    },
    # === Filtros flutuantes (caixa de busca abaixo do header) ===
    ".ag-floating-filter": {
        "background-color": "#FFFFFF !important",
        "border-top": "1px solid #E5E7EB !important",
    },
    ".ag-floating-filter-input": {
        "font-size": "12px !important",
    },
    # === Linhas zebradas ===
    ".ag-row-odd": {
        "background-color": "#FFFFFF !important",
    },
    ".ag-row-even": {
        "background-color": "#FAFCFB !important",
    },
    # === Hover e seleção ===
    ".ag-row-hover": {
        "background-color": "#E9F7EF !important",
    },
    ".ag-row-selected": {
        "background-color": "#E9F7EF !important",
    },
    # === Bordas arredondadas ===
    ".ag-root-wrapper": {
        "border": "1px solid #E5E7EB !important",
        "border-radius": "10px !important",
        "overflow": "hidden !important",
    },
    # === Células ===
    ".ag-cell": {
        "font-size": "13px !important",
        "color": "#1A1A1A !important",
    },
    ".ag-row": {
        "font-size": "13px !important",
    },
}


def tabela(
    df: pd.DataFrame,
    altura: int = 400,
    busca: bool = True,
    filtros: bool = True,
    paginacao: bool = False,
    paginacao_size: int = 20,
    selecao: str = None,
    largura_colunas: str = "FIT_CONTENTS",
    key: str = None,
):
    """
    Exibe tabela padronizada com AgGrid.
    - Header preto/bold com linha verde abaixo
    - Filtros flutuantes (caixa abaixo do header)
    - 3 pontos do menu sempre visíveis (autosize, pin, hide, etc.)
    """
    if df is None or df.empty:
        return None

    gb = GridOptionsBuilder.from_dataframe(df)

    # === Colunas padrão ===
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        filter=filtros,
        suppressMenu=False,
        menuTabs=["generalMenuTab", "filterMenuTab", "columnsMenuTab"],
        floatingFilter=filtros,  # caixa de filtro sempre visível
        cellStyle={
            "fontSize": "13px",
            "color": "#1A1A1A",
            "fontFamily": "Helvetica Neue, sans-serif",
        },
    )

    # === Opções gerais do grid ===
    gb.configure_grid_options(
        headerHeight=36,
        rowHeight=32,
        domLayout="normal",
        suppressMenuHide=True,  # ⚡ mantém ícone de menu (3 pontos) SEMPRE visível
        suppressColumnVirtualisation=True,
        suppressContextMenu=False,
        enableRangeSelection=True,
    )

    # === Busca global ===
    if busca:
        gb.configure_grid_options(
            enableQuickFilter=True,
            cacheQuickFilter=True,
        )

    # === Paginação ===
    if paginacao:
        gb.configure_pagination(
            paginationAutoPageSize=False,
            paginationPageSize=paginacao_size,
        )

    # === Seleção ===
    if selecao:
        gb.configure_selection(
            selection_mode=selecao,
            use_checkbox=(selecao == "multiple"),
        )

    grid_options = gb.build()

    # Autosize ao carregar
    grid_options["onFirstDataRendered"] = JsCode(
        "function(params) { params.api.sizeColumnsToFit(); }"
    )

    # Modo de ajuste de colunas
    auto_size_mode = (
        ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW
        if largura_colunas == "FIT_ALL_COLUMNS_TO_VIEW"
        else ColumnsAutoSizeMode.FIT_CONTENTS
    )

    return AgGrid(
        df,
        gridOptions=grid_options,
        height=altura,
        theme="streamlit",
        custom_css=CUSTOM_CSS,
        columns_auto_size_mode=auto_size_mode,
        update_mode=GridUpdateMode.NO_UPDATE,        # ⚡ evita re-render que esconde menu
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,                     # ⚡ permite código JS customizado
        enable_enterprise_modules=True,               # ⚡ habilita 3 pontos + opções avançadas
        use_container_width=True,
        key=key,
    )
