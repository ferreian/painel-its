import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import aplicar_tema, page_header, secao_titulo, imagem_base64
from src.auth import requer_login, usuario_atual, logout, registrar_log, eh_admin
from src.conexao import (
    listar_relatorios,
    carregar_mapeamento,
    substituir_dados,
    get_header_row,
    PLANILHAS,
    sincronizar_pares_cooperante,
)
from src.validacao import validar_colunas, aplicar_mapeamento, converter_tipos
from src.aggrid_helper import tabela


st.set_page_config(
    page_title="Upload - ITS",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_tema()

# === Verifica login ===
requer_login()

# === Só admin acessa esta página ===
if not eh_admin():
    st.error("⛔ Acesso restrito a administradores.")
    st.info("👈 Volte para a página **Home** pelo menu lateral.")
    st.stop()

# === Sidebar com info do usuário ===
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

# === Header customizado com ilustração Upload-cuate ===
upload_img = imagem_base64("Upload-cuate.png")
upload_img_html = (
    f'<img src="{upload_img}" style="height:200px;width:auto;" />'
    if upload_img
    else '<span style="font-size:2.5rem;">📤</span>'
)

st.markdown(f"""
<div class="its-header" style="align-items:center;">
    {upload_img_html}
    <div class="its-header-divider" style="height:100px;"></div>
    <div class="its-header-text">
        <h1>Upload de Dados</h1>
        <div style="font-size:20px;color:#1A1A1A;font-weight:500;margin-top:8px;">
            Carregamento e validação dos relatórios operacionais
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Função genérica do fluxo de upload (uma por aba)
# ============================================================
def fluxo_upload(tipo: str):
    """Renderiza o fluxo completo de upload para um relatório."""
    config = PLANILHAS[tipo]
    label = config["label"]

    secao_titulo(
        label="ESTRUTURA ESPERADA",
        titulo="Confira as colunas antes de subir o arquivo",
    )

    # === Carrega o DePara ===
    try:
        with st.spinner(f"Carregando mapeamento..."):
            df_mapeamento = carregar_mapeamento(tipo)
    except Exception as e:
        st.error(f"Erro ao carregar mapeamento: {e}")
        return

    with st.expander(f"Ver detalhes da estrutura — {len(df_mapeamento)} colunas"):
        # Renomeia as colunas só para exibição (não mexe nos dados originais)
        df_mapeamento_view = df_mapeamento.rename(columns={
            "nome_excel": "nome_original",
            "nome_destino": "nome_base",
        })
        tabela(df_mapeamento_view, altura=400, key=f"depara_renomeado_{tipo}")

    # === ETAPA 1: Upload ===
    secao_titulo(
        label="ETAPA 1",
        titulo="Selecione o arquivo",
        descricao="Aceita arquivos Excel (.xlsx ou .xls).",
    )

    arquivo = st.file_uploader(
        "Arraste o arquivo aqui ou clique para selecionar",
        type=["xlsx", "xls"],
        label_visibility="collapsed",
        key=f"upload_{tipo}",
    )

    if arquivo is None:
        st.markdown(
            "<div style='background-color:#E9F7EF;border-left:4px solid #27AE60;"
            "padding:12px 16px;border-radius:8px;margin:1rem 0;'>"
            "<span style='color:#1E8449;font-size:14px;font-weight:500;'>"
            "Aguardando upload do arquivo..."
            "</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # === Lê o Excel ===
    try:
        header_row = get_header_row(tipo)
        df_excel = pd.read_excel(arquivo, dtype=str, header=header_row)
        df_excel = df_excel.dropna(axis=1, how="all")
        df_excel = df_excel.loc[:, ~df_excel.columns.astype(str).str.startswith("Unnamed:")]
    except Exception as e:
        st.error(f"Erro ao ler o Excel: {e}")
        return

    st.success(
        f"Arquivo carregado: **{arquivo.name}** — "
        f"{df_excel.shape[0]:,} linhas, {df_excel.shape[1]} colunas".replace(",", ".")
    )

    # === ETAPA 2: Validação ===
    secao_titulo(
        label="ETAPA 2",
        titulo="Validação das colunas",
        descricao="Comparação automática entre o arquivo enviado e o mapeamento oficial.",
    )

    resultado = validar_colunas(df_excel, df_mapeamento)

    col1, col2, col3 = st.columns(3)
    col1.metric("Colunas esperadas", len(df_mapeamento))
    col2.metric("Colunas no arquivo", df_excel.shape[1])
    col3.metric("Status", "OK" if resultado["ok"] else "Atenção")

    if resultado["faltando"]:
        st.error("**Colunas faltando no Excel:**")
        for c in resultado["faltando"]:
            st.write(f"• `{c}`")

    if resultado["extras"]:
        st.warning("**Colunas extras no Excel (serão ignoradas):**")
        for c in resultado["extras"]:
            st.write(f"• `{c}`")

    if resultado["fora_de_ordem"]:
        st.info("Algumas colunas estão fora de ordem — serão reordenadas automaticamente.")
        with st.expander("Ver detalhes da ordem"):
            tabela(pd.DataFrame(resultado["fora_de_ordem"]), altura=300, key=f"ordem_{tipo}")

    if resultado["faltando"]:
        st.error("Existem colunas obrigatórias faltando. Corrija o arquivo e tente novamente.")
        return

    # === ETAPA 3: Processamento ===
    secao_titulo(
        label="ETAPA 3",
        titulo="Processamento dos dados",
        descricao="Aplicação do mapeamento e conversão automática de tipos.",
    )

    try:
        with st.spinner("Aplicando mapeamento e convertendo tipos..."):
            df_tratado = aplicar_mapeamento(df_excel, df_mapeamento)
            df_tratado = converter_tipos(df_tratado)
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return

    st.success(
        f"Dados processados: **{df_tratado.shape[0]:,}** linhas, "
        f"**{df_tratado.shape[1]}** colunas".replace(",", ".")
    )

    with st.expander("Preview dos dados tratados (primeiras 20 linhas)", expanded=True):
        tabela(df_tratado.head(20), altura=500, key=f"preview_{tipo}")

    with st.expander("Resumo das colunas"):
        tipos = pd.DataFrame({
            "coluna": df_tratado.columns,
            "tipo": df_tratado.columns.map(
                lambda c: "data" if c.startswith("dt_")
                else "valor" if c.startswith("vl_")
                else "quantidade" if c.startswith("qt_")
                else "código" if c.startswith("cod_")
                else "categoria" if c.startswith("cat_")
                else "texto"
            ),
            "nulos": df_tratado.isna().sum().values,
        }).reset_index(drop=True)
        tabela(tipos, altura=400, key=f"tipos_resumo_{tipo}")

    # === ETAPA 4: Gravação ===
    secao_titulo(
        label="ETAPA 4",
        titulo="Salvar na base de dados",
        descricao="Atenção: a base de dados atual será substituída pelo novo conteúdo.",
    )

    confirma = st.checkbox(
        "Estou ciente que os dados atuais serão substituídos",
        key=f"confirma_{tipo}",
    )

    if confirma:
        if st.button("Salvar dados", type="primary", key=f"gravar_{tipo}"):
            try:
                with st.spinner("Salvando dados..."):
                    qtd = substituir_dados(df_tratado, tipo)

                # Log de sucesso
                registrar_log(
                    email=user["email"],
                    acao="upload",
                    relatorio=tipo,
                    linhas=qtd,
                    sucesso=True,
                    detalhe=f"arquivo: {arquivo.name}",
                )

                st.success(f"{qtd:,} registros salvos com sucesso!".replace(",", "."))
                st.toast("Dados atualizados", icon="✅")

                # === Sincroniza tabela isCooperante (somente Multiplication) ===
                if tipo == "multiplication":
                    try:
                        with st.spinner("Sincronizando classificação de áreas..."):
                            novos, aguardando = sincronizar_pares_cooperante(
                                df_tratado, email_usuario=user["email"]
                            )

                        if novos > 0:
                            st.markdown(
                                f"<div style='background-color:#FEF3C7;border-left:4px solid #F59E0B;"
                                f"padding:12px 16px;border-radius:8px;margin:1rem 0;'>"
                                f"<span style='color:#92400E;font-size:14px;font-weight:500;'>"
                                f"<b>{novos}</b> novo(s) par(es) Filial → Cooperante adicionado(s). "
                                f"<b>{aguardando}</b> aguardando classificação na página <b>Cadastros</b>."
                                f"</span></div>",
                                unsafe_allow_html=True,
                            )
                            st.toast(f"{novos} pares novos para classificar", icon="📋")
                        elif aguardando > 0:
                            st.markdown(
                                f"<div style='background-color:#FEF3C7;border-left:4px solid #F59E0B;"
                                f"padding:12px 16px;border-radius:8px;margin:1rem 0;'>"
                                f"<span style='color:#92400E;font-size:14px;font-weight:500;'>"
                                f"Nenhum par novo. <b>{aguardando}</b> ainda aguardam classificação na página <b>Cadastros</b>."
                                f"</span></div>",
                                unsafe_allow_html=True,
                            )
                    except Exception as e:
                        st.warning(f"Dados salvos, mas falhou ao sincronizar classificação de áreas: {e}")

                st.cache_data.clear()

                # Mensagem contextualizada de acordo com o tipo
                if tipo == "multiplication":
                    st.markdown(
                        "<div style='background-color:#E9F7EF;border-left:4px solid #27AE60;"
                        "padding:12px 16px;border-radius:8px;margin:1rem 0;'>"
                        "<span style='color:#1E8449;font-size:14px;font-weight:500;'>"
                        "Acesse a página <b>Multiplication Report</b> no menu lateral para conferir os dados."
                        "</span></div>",
                        unsafe_allow_html=True,
                    )
                elif tipo == "sales":
                    st.markdown(
                        "<div style='background-color:#E9F7EF;border-left:4px solid #27AE60;"
                        "padding:12px 16px;border-radius:8px;margin:1rem 0;'>"
                        "<span style='color:#1E8449;font-size:14px;font-weight:500;'>"
                        "Os dados foram atualizados na base."
                        "</span></div>",
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                # Log de erro
                registrar_log(
                    email=user["email"],
                    acao="upload",
                    relatorio=tipo,
                    sucesso=False,
                    detalhe=str(e)[:100],
                )
                st.error(f"Erro ao salvar: {e}")


# ============================================================
# Abas
# ============================================================
relatorios = listar_relatorios()
abas = st.tabs([label for _, label in relatorios])

for aba, (tipo, _label) in zip(abas, relatorios):
    with aba:
        fluxo_upload(tipo)
