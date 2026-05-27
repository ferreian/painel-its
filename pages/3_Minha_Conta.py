import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import aplicar_tema, page_header, secao_titulo
from src.auth import (
    requer_login,
    usuario_atual,
    logout,
    trocar_senha,
    verificar_senha,
    buscar_usuario,
    registrar_log,
)


st.set_page_config(
    page_title="Minha Conta - ITS",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_tema()
requer_login()

# CSS local da página: botão verde
st.markdown("""
<style>
    /* Botão verde primário no form */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button[kind="primary"] {
        background-color: #27AE60 !important;
        border-color: #27AE60 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
    div[data-testid="stForm"] button[kind="primary"]:hover {
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
    titulo="Minha Conta",
    subtitulo="Dados do seu acesso",
)

# === Informações da conta ===
secao_titulo(
    label="DADOS PESSOAIS",
    titulo="Suas informações",
)

col1, col2, col3 = st.columns(3)
col1.metric("Nome", user["nome"])
col2.metric("Email", user["email"])
col3.metric("Papel", user["papel"].upper())

st.caption("Para alterar nome, email ou papel, procure um administrador.")

st.divider()

# === Trocar senha (formulário compacto e centralizado) ===
secao_titulo(
    label="SEGURANÇA",
    titulo="Trocar minha senha",
    descricao="Recomendamos trocar sua senha periodicamente.",
)

# Centraliza o formulário usando 3 colunas
col_esq, col_meio, col_dir = st.columns([1, 1, 1])

with col_meio:
    with st.container(border=True):
        st.markdown(
            "<div style='text-align:center;margin-bottom:1rem;"
            "padding-bottom:0.8rem;border-bottom:1px solid #E5E7EB;'>"
            "<p style='font-size:1rem;margin:0;font-weight:600;display:flex;"
            "align-items:center;justify-content:center;gap:8px;'>"
            "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' "
            "xmlns='http://www.w3.org/2000/svg'>"
            "<rect x='4' y='10' width='16' height='11' rx='2' fill='#F4B400'/>"
            "<path d='M7 10V7a5 5 0 0110 0v3' stroke='#1E8449' stroke-width='2.2' "
            "stroke-linecap='round'/>"
            "<circle cx='12' cy='15' r='1.5' fill='#1A1A1A'/>"
            "<rect x='11.4' y='15' width='1.2' height='3' fill='#1A1A1A'/>"
            "</svg>"
            "<span style='color:#1A1A1A;'>Atualizar senha</span>"
            "</p>"
            "<p style='font-size:0.82rem;color:#6B7280;margin:0.3rem 0 0;'>"
            "Preencha os campos abaixo"
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        with st.form("form_trocar_senha", clear_on_submit=True):
            senha_atual = st.text_input("Senha atual", type="password",
                                        placeholder="••••••••")
            nova_senha = st.text_input("Nova senha", type="password",
                                       placeholder="Mínimo 6 caracteres",
                                       help="Mínimo 6 caracteres")
            confirma_senha = st.text_input("Confirme a nova senha",
                                           type="password",
                                           placeholder="••••••••")

            submit = st.form_submit_button("Atualizar senha", type="primary",
                                           use_container_width=True)

            if submit:
                if not senha_atual or not nova_senha or not confirma_senha:
                    st.error("Preencha todos os campos.")
                elif nova_senha != confirma_senha:
                    st.error("A nova senha e a confirmação não conferem.")
                elif len(nova_senha) < 6:
                    st.error("A nova senha precisa ter pelo menos 6 caracteres.")
                elif nova_senha == senha_atual:
                    st.error("A nova senha não pode ser igual à atual.")
                else:
                    try:
                        usuario_db = buscar_usuario(user["email"])
                        if not usuario_db or not verificar_senha(
                            senha_atual, usuario_db["senha_hash"]
                        ):
                            st.error("Senha atual incorreta.")
                        else:
                            sucesso, msg = trocar_senha(user["email"], nova_senha)
                            if sucesso:
                                registrar_log(user["email"], "trocou_senha")
                                st.success("✅ Senha atualizada com sucesso!")
                            else:
                                st.error(msg)
                    except Exception as e:
                        st.error(f"Erro: {e}")
