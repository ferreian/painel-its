"""
Home.py — página inicial do Painel ITS
Funciona localmente com cred.json + .streamlit/secrets.toml
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.theme import aplicar_tema, secao_titulo, imagem_base64
from src.auth import requer_login, usuario_atual, logout, eh_admin


# === Configuração da página ===
st.set_page_config(
    page_title="Visão Operacional: Multiplication & Sales Report",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_tema()

# === Verifica login (bloqueia se não estiver logado) ===
requer_login()

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


# === Header com logo + imagem ===
logo_img = imagem_base64("logo.png")
report_img = imagem_base64("Online report-bro.png")

logo_html = (
    f'<img src="{logo_img}" style="height:80px;width:auto;" />'
    if logo_img
    else '<span style="font-size:2.5rem;">🌱</span>'
)

st.markdown(f"""
<div class="its-header" style="align-items:center;">
    {logo_html}
    <div class="its-header-divider" style="height:80px;"></div>
    <div class="its-header-text">
        <h1>Visão Operacional</h1>
        <div style="font-size:20px;color:#1A1A1A;font-weight:500;margin-top:8px;">
            Multiplication & Sales Report — Stine Seed
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


st.markdown("<div style='margin:2rem 0;'></div>", unsafe_allow_html=True)


# === Mensagem de boas-vindas ===
st.markdown(f"""
<div style='background:#FFFFFF;border:1px solid #E5E7EB;border-left:4px solid #27AE60;
border-radius:10px;padding:24px;margin-bottom:1.5rem;'>
<p style='font-size:14px;color:#6B7280;text-transform:uppercase;letter-spacing:0.05em;
font-weight:600;margin:0 0 8px;'>BEM-VINDO(A)</p>
<p style='font-size:22px;color:#1A1A1A;font-weight:600;margin:0 0 12px;'>
Olá, {user['nome']}!
</p>
<p style='font-size:15px;color:#374151;margin:0;line-height:1.6;'>
Acesse os módulos pelo <b>menu lateral</b> à esquerda.
Você pode visualizar o <b>Multiplication Report</b>, gerenciar <b>Cadastros</b>
{'e fazer <b>Upload</b> de novos dados' if eh_admin() else ''}.
</p>
</div>
""", unsafe_allow_html=True)


# === Páginas disponíveis ===
secao_titulo(
    label="PÁGINAS DO PAINEL",
    titulo="O que você quer fazer hoje?",
    descricao="Selecione um módulo no menu lateral para começar.",
)

# Layout: cards à esquerda + imagem à direita
col_cards, col_imagem = st.columns([2, 1])

with col_cards:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style='background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;padding:20px;margin-bottom:1rem;'>
        <p style='font-size:24px;margin:0 0 8px;'>📊</p>
        <p style='font-size:18px;font-weight:700;color:#1A1A1A;margin:0 0 4px;'>Multiplication Report</p>
        <p style='font-size:13px;color:#6B7280;margin:0 0 12px;'>Análise principal</p>
        <p style='font-size:14px;color:#374151;margin:0;'>
        Auditoria de dados, filtros hierárquicos, gráficos analíticos e relatório consolidado.
        </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;padding:20px;margin-bottom:1rem;'>
        <p style='font-size:24px;margin:0 0 8px;'>📋</p>
        <p style='font-size:18px;font-weight:700;color:#1A1A1A;margin:0 0 4px;'>Cadastros</p>
        <p style='font-size:13px;color:#6B7280;margin:0 0 12px;'>Classificação de áreas</p>
        <p style='font-size:14px;color:#374151;margin:0;'>
        Classifique pares Filial → Cooperante como área própria ou de cooperante.
        </p>
        </div>
        """, unsafe_allow_html=True)


    if eh_admin():
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("""
            <div style='background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;padding:20px;margin-bottom:1rem;'>
            <p style='font-size:24px;margin:0 0 8px;'>📤</p>
            <p style='font-size:18px;font-weight:700;color:#1A1A1A;margin:0 0 4px;'>Upload</p>
            <p style='font-size:13px;color:#6B7280;margin:0 0 12px;'>Atualização da base</p>
            <p style='font-size:14px;color:#374151;margin:0;'>
            Faça upload e validação de novos arquivos do Multiplication e Sales Report.
            </p>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown("""
            <div style='background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;padding:20px;margin-bottom:1rem;'>
            <p style='font-size:24px;margin:0 0 8px;'>⚙️</p>
            <p style='font-size:18px;font-weight:700;color:#1A1A1A;margin:0 0 4px;'>Admin</p>
            <p style='font-size:13px;color:#6B7280;margin:0 0 12px;'>Gerenciamento</p>
            <p style='font-size:14px;color:#374151;margin:0;'>
            Cadastre usuários, defina permissões e consulte logs de acesso.
            </p>
            </div>
            """, unsafe_allow_html=True)

with col_imagem:
    if report_img:
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:center;height:100%;padding:1rem;">'
            f'<img src="{report_img}" style="max-width:100%;height:auto;" />'
            f'</div>',
            unsafe_allow_html=True,
        )
