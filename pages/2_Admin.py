import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import aplicar_tema, page_header, secao_titulo
from src.aggrid_helper import tabela
from src.auth import (
    requer_login,
    usuario_atual,
    logout,
    eh_admin,
    carregar_usuarios,
    cadastrar_usuario,
    desativar_usuario,
    reativar_usuario,
    resetar_senha,
    carregar_logs,
)


st.set_page_config(
    page_title="Admin - ITS",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_tema()
requer_login()

# Só admin acessa
if not eh_admin():
    st.error("⛔ Acesso restrito a administradores.")
    st.info("👈 Volte para a página **Home** ou **Upload**.")
    st.stop()

# CSS local: botão verde + ações verdes em geral
st.markdown("""
<style>
    /* Botão verde primário em formulários */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button[kind="primary"],
    .stButton > button[kind="primary"] {
        background-color: #27AE60 !important;
        border-color: #27AE60 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
    div[data-testid="stForm"] button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:hover {
        background-color: #1E8449 !important;
        border-color: #1E8449 !important;
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

page_header(
    titulo="Administração",
    subtitulo="Gestão de usuários e auditoria de acessos",
)


# === Abas ===
aba_usuarios, aba_novo, aba_logs = st.tabs(["👥 Usuários", "➕ Cadastrar", "📜 Logs"])


# ============================================================
# ABA 1: Usuários
# ============================================================
with aba_usuarios:
    secao_titulo(
        label="USUÁRIOS",
        titulo="Lista de usuários cadastrados",
        descricao="Gerencie o acesso e resete senhas quando necessário.",
    )

    try:
        df_users = carregar_usuarios()

        if df_users.empty:
            st.info("Nenhum usuário cadastrado ainda.")
        else:
            colunas_view = ["nome", "email", "papel", "ativo"]
            if "precisa_trocar_senha" in df_users.columns:
                colunas_view.append("precisa_trocar_senha")

            df_view = df_users[colunas_view].copy()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total de usuários", len(df_view))
            col2.metric("Ativos", (df_view["ativo"].str.lower() == "sim").sum())
            if "precisa_trocar_senha" in df_view.columns:
                col3.metric(
                    "Aguardando 1º acesso",
                    (df_view["precisa_trocar_senha"].str.lower() == "sim").sum(),
                )

            tabela(df_view, altura=300, key="lista_usuarios")

            st.divider()

            # Card centralizado para ações
            col_esq, col_meio, col_dir = st.columns([1, 1.5, 1])
            with col_meio:
                with st.container(border=True):
                    st.markdown(
                        "<div style='text-align:center;margin-bottom:1rem;"
                        "padding-bottom:0.8rem;border-bottom:1px solid #E5E7EB;'>"
                        "<p style='font-size:1rem;margin:0;font-weight:600;display:flex;"
                        "align-items:center;justify-content:center;gap:8px;'>"
                        "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' "
                        "xmlns='http://www.w3.org/2000/svg'>"
                        "<path d='M12 2L4 6v6c0 5 3.5 9.5 8 10 4.5-.5 8-5 8-10V6l-8-4z' "
                        "fill='#27AE60'/>"
                        "<path d='M9 12l2 2 4-4' stroke='#FFFFFF' stroke-width='2' "
                        "stroke-linecap='round' stroke-linejoin='round' fill='none'/>"
                        "</svg>"
                        "<span style='color:#1A1A1A;'>Ações no usuário</span>"
                        "</p>"
                        "<p style='font-size:0.82rem;color:#6B7280;margin:0.3rem 0 0;'>"
                        "Selecione um usuário e a ação"
                        "</p>"
                        "</div>",
                        unsafe_allow_html=True,
                    )

                    email_alvo = st.selectbox(
                        "Email",
                        options=df_view["email"].tolist(),
                    )
                    acao = st.selectbox(
                        "Ação",
                        options=["Desativar", "Reativar", "Resetar senha"],
                    )
                    aplicar_btn = st.button(
                        "Aplicar", type="primary", use_container_width=True
                    )

                    if aplicar_btn:
                        if email_alvo == user["email"]:
                            st.error("Você não pode aplicar ações ao seu próprio usuário.")
                        else:
                            try:
                                if acao == "Desativar":
                                    ok, msg = desativar_usuario(email_alvo)
                                    if ok:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                                elif acao == "Reativar":
                                    ok, msg = reativar_usuario(email_alvo)
                                    if ok:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                                elif acao == "Resetar senha":
                                    ok, msg, nova_senha = resetar_senha(email_alvo)
                                    if ok:
                                        st.success(msg)
                                        st.warning(
                                            "**Envie esta senha temporária para o usuário.** "
                                            "Ele precisará trocá-la no primeiro acesso."
                                        )
                                        st.code(nova_senha, language=None)
                                    else:
                                        st.error(msg)
                            except Exception as e:
                                st.error(f"Erro: {e}")

    except Exception as e:
        st.error(f"Erro ao carregar usuários: {e}")


# ============================================================
# ABA 2: Cadastrar novo usuário
# ============================================================
with aba_novo:
    secao_titulo(
        label="NOVO USUÁRIO",
        titulo="Cadastrar acesso",
        descricao="O sistema gera uma senha temporária. O usuário será obrigado a trocá-la no primeiro acesso.",
    )

    # Card centralizado
    col_esq, col_meio, col_dir = st.columns([1, 1.5, 1])
    with col_meio:
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center;margin-bottom:1rem;"
                "padding-bottom:0.8rem;border-bottom:1px solid #E5E7EB;'>"
                "<p style='font-size:1rem;margin:0;font-weight:600;display:flex;"
                "align-items:center;justify-content:center;gap:8px;'>"
                "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' "
                "xmlns='http://www.w3.org/2000/svg'>"
                "<circle cx='12' cy='8' r='4' fill='#27AE60'/>"
                "<path d='M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8' fill='#27AE60'/>"
                "<circle cx='19' cy='6' r='4' fill='#F4B400'/>"
                "<path d='M19 4v4M17 6h4' stroke='#FFFFFF' stroke-width='1.8' "
                "stroke-linecap='round'/>"
                "</svg>"
                "<span style='color:#1A1A1A;'>Cadastrar acesso</span>"
                "</p>"
                "<p style='font-size:0.82rem;color:#6B7280;margin:0.3rem 0 0;'>"
                "Preencha os dados do novo usuário"
                "</p>"
                "</div>",
                unsafe_allow_html=True,
            )

            with st.form("form_novo_usuario", clear_on_submit=False):
                nome = st.text_input("Nome completo *",
                                     placeholder="Nome e sobrenome")
                email = st.text_input("Email *",
                                      placeholder="usuario@empresa.com")
                papel = st.radio("Papel *",
                                 options=["usuario", "admin"],
                                 horizontal=True)

                st.caption("\\* Campos obrigatórios")

                submit = st.form_submit_button("Cadastrar usuário",
                                               type="primary",
                                               use_container_width=True)

                if submit:
                    try:
                        ok, msg, senha_temp = cadastrar_usuario(nome, email, papel)
                        if ok:
                            st.success(msg)
                            st.divider()
                            st.markdown("**📧 Envie estas informações ao usuário:**")

                            st.markdown("Email:")
                            st.code(email.strip().lower(), language=None)
                            st.markdown("Senha temporária:")
                            st.code(senha_temp, language=None)

                            st.warning(
                                "⚠️ **Anote a senha temporária agora** — ela não "
                                "será exibida novamente. O usuário será obrigado a "
                                "definir uma nova senha no primeiro login."
                            )
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")


# ============================================================
# ABA 3: Logs
# ============================================================
with aba_logs:
    secao_titulo(
        label="AUDITORIA",
        titulo="Histórico de acessos e uploads",
        descricao="Os 100 registros mais recentes (do mais novo para o mais antigo).",
    )

    try:
        df_logs = carregar_logs(limite=100)

        if df_logs.empty:
            st.info("📭 Nenhum log registrado ainda. Os logs aparecerão aqui conforme os usuários acessarem o sistema.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total exibido", len(df_logs))

            if "acao" in df_logs.columns:
                uploads = (df_logs["acao"] == "upload").sum()
                logins = (df_logs["acao"] == "login_sucesso").sum()
                col2.metric("Uploads", uploads)
                col3.metric("Logins", logins)

            tabela(df_logs, altura=500, paginacao=True, paginacao_size=20, key="logs_tabela")

    except Exception as e:
        mensagem = str(e)
        if "logs" in mensagem.lower() or "worksheet" in mensagem.lower():
            st.error(
                "❌ **Aba 'logs' não encontrada na planilha ITS_Usuarios.**\n\n"
                "Para resolver:\n"
                "1. Abra a planilha ITS_Usuarios no Google Sheets\n"
                "2. Crie uma aba chamada exatamente `logs` (minúsculo, sem espaço)\n"
                "3. Na linha 1, adicione os cabeçalhos: "
                "`data_hora`, `email`, `acao`, `relatorio`, `linhas`, `sucesso`, `detalhe`"
            )
        else:
            st.error(f"Erro ao carregar logs: {e}")
