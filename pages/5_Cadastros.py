"""
pages/5_Cadastros.py — Cadastros (classificação de áreas)
Estrutura híbrida: AgGrid para auditoria + data_editor para classificar.
"""
import io
from datetime import datetime
import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import aplicar_tema, secao_titulo, imagem_base64
from src.auth import requer_login, usuario_atual, logout, eh_admin, registrar_log
from src.conexao import carregar_is_cooperante, salvar_is_cooperante
from src.aggrid_helper import tabela


st.set_page_config(
    page_title="Cadastros - ITS",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_tema()
requer_login()

# Só admin acessa
if not eh_admin():
    st.error("⛔ Acesso restrito a administradores.")
    st.info("👈 Volte para a página **Home** pelo menu lateral.")
    st.stop()

# CSS local: botão verde + cabeçalho preto no data_editor
st.markdown("""
<style>
    /* Botões primary verdes */
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"],
    div[data-testid="stForm"] button[kind="primary"] {
        background-color: #27AE60 !important;
        border-color: #27AE60 !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover,
    div[data-testid="stForm"] button[kind="primary"]:hover {
        background-color: #1E8449 !important;
        border-color: #1E8449 !important;
    }

    /* ============================================================
       CABEÇALHO DO st.data_editor — força preto bold
       ============================================================ */

    /* Captura todo header de qualquer dataframe/editor */
    div[data-testid="stDataFrame"] [role="columnheader"],
    div[data-testid="stDataFrameResizable"] [role="columnheader"],
    [data-testid="stDataEditor"] [role="columnheader"],
    .stDataFrame [role="columnheader"],
    [class*="stDataEditor"] [role="columnheader"] {
        background-color: #F8FAF9 !important;
        color: #1A1A1A !important;
    }

    /* Texto interno do header */
    div[data-testid="stDataFrame"] [role="columnheader"] *,
    div[data-testid="stDataFrameResizable"] [role="columnheader"] *,
    [data-testid="stDataEditor"] [role="columnheader"] *,
    .stDataFrame [role="columnheader"] *,
    [class*="stDataEditor"] [role="columnheader"] * {
        color: #1A1A1A !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #1A1A1A !important;
    }

    /* Tenta capturar via canvas grid (data_editor moderno usa canvas) */
    iframe[title*="streamlit_data_editor"] {
        color-scheme: light !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
user = usuario_atual()
with st.sidebar:
    st.markdown(
        f"<div style='padding:1rem 0.5rem;border-bottom:1px solid #E5E7EB;margin-bottom:1rem;'>"
        f"<p style='font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:0.05em;"
        f"font-weight:600;margin:0 0 4px;'>USUÁRIO</p>"
        f"<p style='font-size:14px;color:#1A1A1A;font-weight:600;margin:0;'>{user['nome']}</p>"
        f"<p style='font-size:12px;color:#6B7280;margin:0;'>{user['email']}</p>"
        f"<p style='font-size:11px;color:#27AE60;font-weight:600;margin:4px 0 0;text-transform:uppercase;'>"
        f"{user['papel']}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("Sair", use_container_width=True):
        logout()
        st.rerun()


# Header
st.markdown(f"""
<div class="its-header" style="align-items:center;">
    <div style="font-size:3rem;">📋</div>
    <div class="its-header-divider" style="height:80px;"></div>
    <div class="its-header-text">
        <h1>Cadastros</h1>
        <div style="font-size:18px;color:#1A1A1A;font-weight:500;margin-top:8px;">
            Classificação de áreas: próprias ou de cooperantes
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Carrega dados
# ============================================================
try:
    df = carregar_is_cooperante()

    if df.empty:
        st.markdown(
            "<div style='background-color:#FEF3C7;border-left:4px solid #F59E0B;"
            "padding:12px 16px;border-radius:8px;margin:1rem 0;'>"
            "<span style='color:#92400E;font-size:14px;font-weight:500;'>"
            "Nenhum par cadastrado ainda. Faça um upload do Multiplication Report primeiro."
            "</span></div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # Normaliza is_cooperante para booleano (True/False)
    df["is_cooperante_bool"] = (
        df["cat_is_cooperante"].astype(str).str.strip().str.lower().isin(["sim", "true", "1", "s"])
    )

    # === Métricas no topo (sempre visíveis) ===
    total = len(df)
    classificados = (df["cat_is_cooperante"].astype(str).str.strip() != "").sum()
    aguardando = total - classificados
    cooperantes = df["is_cooperante_bool"].sum()
    proprias = classificados - cooperantes

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de pares", total)
    col2.metric("Cooperantes", cooperantes)
    col3.metric("Áreas próprias", proprias)
    col4.metric("Aguardando", aguardando)

    st.markdown("<div style='margin:1rem 0;'></div>", unsafe_allow_html=True)


    # ============================================================
    # Estrutura híbrida com abas
    # ============================================================
    tab_auditoria, tab_classificar = st.tabs(["🔍 Auditoria", "✏️ Classificar"])


    # ============================================================
    # ABA 1: Auditoria (AgGrid - só leitura)
    # ============================================================
    with tab_auditoria:
        secao_titulo(
            label="AUDITORIA",
            titulo="Ver classificações",
            descricao="Consulte com filtros e busca todos os pares Filial → Cooperante já cadastrados.",
        )

        # Prepara DataFrame para exibição (nomes amigáveis)
        df_view = df[[
            "desc_razao_social_filial",
            "cod_cnpj_filial",
            "desc_nome_cooperante",
            "cod_cpf_cnpj_cooperante",
            "cat_is_cooperante",
            "dt_atualizacao",
            "desc_usuario_classificou",
        ]].copy()

        # Converte cat_is_cooperante para "Sim" / "Não" / "—"
        def formatar_status(v):
            v = str(v).strip().lower()
            if v in ["sim", "true", "1", "s"]:
                return "Sim"
            elif v in ["nao", "não", "false", "0", "n"]:
                return "Não"
            else:
                return "—"

        df_view["cat_is_cooperante"] = df_view["cat_is_cooperante"].apply(formatar_status)

        df_view.columns = [
            "Razão Social Filial",
            "CNPJ Filial",
            "Nome Cooperante",
            "CPF/CNPJ Cooperante",
            "É Cooperante?",
            "Última Atualização",
            "Usuário Classificou",
        ]

        # AgGrid bonito com filtros, busca, paginação
        tabela(
            df_view,
            altura=500,
            busca=True,
            filtros=True,
            paginacao=True,
            paginacao_size=50,
            key="auditoria_cadastros",
        )

        st.markdown("<div style='margin:1rem 0;'></div>", unsafe_allow_html=True)

        # Botão exportar Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_view.to_excel(writer, index=False, sheet_name="Cadastros")
        buffer.seek(0)

        nome_arquivo = f"Cadastros_isCooperante_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        col_btn, _ = st.columns([1, 4])
        with col_btn:
            st.download_button(
                label="📥 Exportar Excel",
                data=buffer,
                file_name=nome_arquivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="exportar_cadastros",
                use_container_width=True,
                type="primary",
            )


    # ============================================================
    # ABA 2: Classificar (data_editor - edição inline)
    # ============================================================
    with tab_classificar:
        secao_titulo(
            label="CLASSIFICAÇÃO",
            titulo="É cooperante?",
            descricao="Marque a coluna 'É Cooperante?' para indicar se o cooperante representa uma área de terceiros. Desmarcado = área própria.",
        )

        # Filtro de visualização
        filtro = st.radio(
            "Mostrar:",
            options=["Todos", "Só aguardando classificação", "Só cooperantes", "Só áreas próprias"],
            horizontal=True,
        )

        if filtro == "Só aguardando classificação":
            df_filt = df[df["cat_is_cooperante"].astype(str).str.strip() == ""].copy()
        elif filtro == "Só cooperantes":
            df_filt = df[df["is_cooperante_bool"]].copy()
        elif filtro == "Só áreas próprias":
            df_filt = df[
                (df["cat_is_cooperante"].astype(str).str.strip() != "")
                & (~df["is_cooperante_bool"])
            ].copy()
        else:
            df_filt = df.copy()

        # Editor
        st.markdown(
            "<p style='font-size:13px;color:#6B7280;margin:0.5rem 0;'>"
            f"Exibindo <b>{len(df_filt)}</b> de <b>{len(df)}</b> registros. "
            "Marque/desmarque a coluna 'É Cooperante?' e clique em <b>Salvar classificações</b>."
            "</p>",
            unsafe_allow_html=True,
        )

        df_editor = df_filt[["desc_razao_social_filial", "desc_nome_cooperante", "is_cooperante_bool"]].copy()
        df_editor.columns = ["Razão Social Filial", "Nome Cooperante", "É Cooperante?"]

        df_editado = st.data_editor(
            df_editor,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            disabled=["Razão Social Filial", "Nome Cooperante"],
            column_config={
                "É Cooperante?": st.column_config.CheckboxColumn(
                    "É Cooperante?",
                    help="Marque se o cooperante é uma área de terceiros (não própria)",
                    default=False,
                ),
            },
            height=500,
            key="editor_cooperante",
        )

        # Botão Salvar
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button("Salvar classificações", type="primary", use_container_width=True):
                try:
                    with st.spinner("Salvando classificações..."):
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                        # Cria dict com as edições do editor
                        edicoes = {
                            (row["Razão Social Filial"], row["Nome Cooperante"]): row["É Cooperante?"]
                            for _, row in df_editado.iterrows()
                        }

                        # Aplica edições + atualiza usuário/data só nos modificados
                        def aplicar_edicao_completa(row):
                            chave = (row["desc_razao_social_filial"], row["desc_nome_cooperante"])
                            if chave in edicoes:
                                novo_valor = "sim" if edicoes[chave] else "nao"
                                valor_anterior = str(row.get("cat_is_cooperante", "")).strip().lower()
                                # Só atualiza data/usuário se o valor mudou
                                if novo_valor != valor_anterior:
                                    return novo_valor, agora, user["email"]
                                return (
                                    novo_valor,
                                    row.get("dt_atualizacao", ""),
                                    row.get("desc_usuario_classificou", ""),
                                )
                            return (
                                row.get("cat_is_cooperante", ""),
                                row.get("dt_atualizacao", ""),
                                row.get("desc_usuario_classificou", ""),
                            )

                        resultados = df.apply(aplicar_edicao_completa, axis=1, result_type="expand")
                        df["cat_is_cooperante"] = resultados[0]
                        df["dt_atualizacao"] = resultados[1]
                        df["desc_usuario_classificou"] = resultados[2]

                        # Salva
                        salvar_is_cooperante(df)

                        registrar_log(
                            email=user["email"],
                            acao="cadastros_cooperante",
                            relatorio="multiplication",
                            linhas=len(df),
                            sucesso=True,
                            detalhe=f"filtro: {filtro}",
                        )

                    st.success("Classificações salvas com sucesso!")
                    st.toast("Cadastros atualizados", icon="✅")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

except Exception as e:
    st.error(f"Erro ao carregar cadastros: {e}")
