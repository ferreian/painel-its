"""
src/auth.py
Autenticação e controle de acesso do painel ITS.
"""

import secrets
import string
from datetime import datetime
from typing import Optional, Tuple

import bcrypt
import pandas as pd
import streamlit as st

from src.conexao import conectar_cliente, USUARIOS_PLANILHA_ID, ABA_USUARIOS, ABA_LOGS


# ============================================================
# Hash de senha
# ============================================================
def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_armazenado.encode("utf-8"))
    except Exception:
        return False


def gerar_senha_temporaria(tamanho: int = 10) -> str:
    """
    Gera uma senha temporária aleatória, fácil de digitar.
    Mistura letras maiúsculas, minúsculas e números (sem caracteres confusos).
    """
    # Evita 0/O, 1/l/I para não confundir
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(chars) for _ in range(tamanho))


# ============================================================
# Acesso à planilha de usuários
# ============================================================
def _abrir_planilha_usuarios():
    client = conectar_cliente()
    return client.open_by_key(USUARIOS_PLANILHA_ID)


def carregar_usuarios() -> pd.DataFrame:
    planilha = _abrir_planilha_usuarios()
    aba = planilha.worksheet(ABA_USUARIOS)
    dados = aba.get_all_records()
    return pd.DataFrame(dados)


def buscar_usuario(email: str) -> Optional[dict]:
    df = carregar_usuarios()
    if df.empty:
        return None

    email_norm = email.strip().lower()
    df["email_norm"] = df["email"].astype(str).str.strip().str.lower()

    encontrado = df[df["email_norm"] == email_norm]
    if encontrado.empty:
        return None

    return encontrado.iloc[0].to_dict()


def cadastrar_usuario(nome: str, email: str, papel: str = "usuario") -> Tuple[bool, str, str]:
    """
    Cadastra um novo usuário com senha temporária aleatória.
    Retorna (sucesso, mensagem, senha_temporaria).
    """
    if not nome.strip() or not email.strip():
        return False, "Nome e email são obrigatórios.", ""

    if papel not in ("admin", "usuario"):
        return False, "Papel inválido.", ""

    if buscar_usuario(email):
        return False, f"Já existe um usuário com o email '{email}'.", ""

    # Gera senha temporária e hash
    senha_temp = gerar_senha_temporaria()
    hash_senha = gerar_hash(senha_temp)

    planilha = _abrir_planilha_usuarios()
    aba = planilha.worksheet(ABA_USUARIOS)
    aba.append_row(
        [nome.strip(), email.strip().lower(), hash_senha, papel, "sim", "sim"],
        value_input_option="USER_ENTERED",
    )

    return True, f"Usuário '{nome}' cadastrado com sucesso!", senha_temp


def trocar_senha(email: str, nova_senha: str) -> Tuple[bool, str]:
    """
    Troca a senha do usuário e marca como 'não precisa trocar'.
    """
    if len(nova_senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."

    planilha = _abrir_planilha_usuarios()
    aba = planilha.worksheet(ABA_USUARIOS)

    valores = aba.get_all_values()
    cabecalho = valores[0]
    try:
        col_email = cabecalho.index("email") + 1
        col_hash = cabecalho.index("senha_hash") + 1
        col_trocar = cabecalho.index("precisa_trocar_senha") + 1
    except ValueError:
        return False, "Estrutura da planilha incorreta. Verifique se a coluna 'precisa_trocar_senha' existe."

    email_norm = email.strip().lower()
    for idx, linha in enumerate(valores[1:], start=2):
        if linha[col_email - 1].strip().lower() == email_norm:
            novo_hash = gerar_hash(nova_senha)
            aba.update_cell(idx, col_hash, novo_hash)
            aba.update_cell(idx, col_trocar, "nao")
            return True, "Senha atualizada com sucesso!"

    return False, "Usuário não encontrado."


def resetar_senha(email: str) -> Tuple[bool, str, str]:
    """
    Reseta a senha de um usuário (gera nova temporária).
    Usado pelo admin quando alguém esquece a senha.
    Retorna (sucesso, mensagem, nova_senha_temporaria).
    """
    planilha = _abrir_planilha_usuarios()
    aba = planilha.worksheet(ABA_USUARIOS)

    valores = aba.get_all_values()
    cabecalho = valores[0]
    try:
        col_email = cabecalho.index("email") + 1
        col_hash = cabecalho.index("senha_hash") + 1
        col_trocar = cabecalho.index("precisa_trocar_senha") + 1
    except ValueError:
        return False, "Estrutura da planilha incorreta.", ""

    email_norm = email.strip().lower()
    for idx, linha in enumerate(valores[1:], start=2):
        if linha[col_email - 1].strip().lower() == email_norm:
            senha_temp = gerar_senha_temporaria()
            novo_hash = gerar_hash(senha_temp)
            aba.update_cell(idx, col_hash, novo_hash)
            aba.update_cell(idx, col_trocar, "sim")
            return True, "Senha resetada com sucesso!", senha_temp

    return False, "Usuário não encontrado.", ""


def desativar_usuario(email: str) -> Tuple[bool, str]:
    return _alterar_status_usuario(email, "nao")


def reativar_usuario(email: str) -> Tuple[bool, str]:
    return _alterar_status_usuario(email, "sim")


def _alterar_status_usuario(email: str, novo_status: str) -> Tuple[bool, str]:
    planilha = _abrir_planilha_usuarios()
    aba = planilha.worksheet(ABA_USUARIOS)

    valores = aba.get_all_values()
    cabecalho = valores[0]
    try:
        col_email = cabecalho.index("email") + 1
        col_ativo = cabecalho.index("ativo") + 1
    except ValueError:
        return False, "Estrutura da planilha incorreta."

    email_norm = email.strip().lower()
    for idx, linha in enumerate(valores[1:], start=2):
        if linha[col_email - 1].strip().lower() == email_norm:
            aba.update_cell(idx, col_ativo, novo_status)
            return True, f"Usuário '{email}' atualizado."

    return False, f"Usuário '{email}' não encontrado."


# ============================================================
# Login
# ============================================================
def fazer_login(email: str, senha: str) -> Tuple[bool, str, Optional[dict]]:
    usuario = buscar_usuario(email)

    if not usuario:
        registrar_log(email, "login_falha", detalhe="email não encontrado")
        return False, "Email ou senha inválidos.", None

    if str(usuario.get("ativo", "")).strip().lower() != "sim":
        registrar_log(email, "login_falha", detalhe="usuário inativo")
        return False, "Usuário inativo. Procure o administrador.", None

    if not verificar_senha(senha, usuario["senha_hash"]):
        registrar_log(email, "login_falha", detalhe="senha incorreta")
        return False, "Email ou senha inválidos.", None

    registrar_log(email, "login_sucesso")

    precisa_trocar = str(usuario.get("precisa_trocar_senha", "nao")).strip().lower() == "sim"

    return True, "Login realizado com sucesso!", {
        "nome": usuario["nome"],
        "email": usuario["email"],
        "papel": usuario["papel"],
        "precisa_trocar_senha": precisa_trocar,
    }


# ============================================================
# Logs
# ============================================================
def registrar_log(
    email: str,
    acao: str,
    relatorio: str = "",
    linhas: int = 0,
    sucesso: bool = True,
    detalhe: str = "",
):
    try:
        planilha = _abrir_planilha_usuarios()
        aba = planilha.worksheet(ABA_LOGS)
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        aba.append_row(
            [agora, email, acao, relatorio, str(linhas), "sim" if sucesso else "nao", detalhe],
            value_input_option="USER_ENTERED",
        )
    except Exception:
        pass


def carregar_logs(limite: int = 100) -> pd.DataFrame:
    planilha = _abrir_planilha_usuarios()
    aba = planilha.worksheet(ABA_LOGS)
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)
    if df.empty:
        return df
    df = df.iloc[::-1].reset_index(drop=True)
    if limite:
        df = df.head(limite)
    return df


# ============================================================
# Helpers de sessão
# ============================================================
def esta_logado() -> bool:
    return st.session_state.get("usuario_logado") is not None


def usuario_atual() -> Optional[dict]:
    return st.session_state.get("usuario_logado")


def eh_admin() -> bool:
    user = usuario_atual()
    return user is not None and user.get("papel") == "admin"


def logout():
    user = usuario_atual()
    if user:
        registrar_log(user["email"], "logout")
    st.session_state["usuario_logado"] = None


# ============================================================
# Tela de troca obrigatória de senha
# ============================================================
def _tela_troca_senha_obrigatoria():
    """Tela mostrada no primeiro login (quando precisa_trocar_senha = sim)."""
    user = usuario_atual()

    # Esconde sidebar e menu de páginas
    st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    .main .block-container {
        padding-top: 2rem !important;
        max-width: 100% !important;
    }
    .login-card input {
        font-size: 13px !important;
        padding: 0.4rem 0.6rem !important;
    }
    /* Botão verde primário (sobrescreve o azul padrão) */
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

    # Logo da Stine no topo
    import base64
    from pathlib import Path
    BASE_DIR = Path(__file__).parent.parent
    logo_src = None
    for ext in ["png", "svg", "jpg", "jpeg"]:
        path = BASE_DIR / "assets" / f"logo.{ext}"
        if path.exists():
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            data = base64.b64encode(path.read_bytes()).decode()
            logo_src = f"data:{mime};base64,{data}"
            break

    logo_html = (
        f'<img src="{logo_src}" style="height:70px;width:auto;margin-bottom:1rem;" />'
        if logo_src else
        '<div style="font-size:2.5rem;margin-bottom:0.5rem;">🌱</div>'
    )

    # Cabeçalho
    st.markdown(f"""
<div style="text-align:center;margin-top:3rem;margin-bottom:1.5rem;">
    {logo_html}
    <h1 style="font-size:1.4rem;font-weight:700;color:#1A1A1A;margin:0;line-height:1.3;">
        Visão Operacional: Multiplication &amp; Sales Report
    </h1>
</div>
""", unsafe_allow_html=True)

    # Card centralizado
    col_esq, col_meio, col_dir = st.columns([1, 1, 1])
    with col_meio:
        with st.container(border=True):
            # Cabeçalho do card
            st.markdown(
                f"<div style='text-align:center;margin-bottom:1rem;"
                f"padding-bottom:0.8rem;border-bottom:1px solid #E5E7EB;'>"
                f"<p style='font-size:1rem;margin:0;font-weight:600;display:flex;align-items:center;justify-content:center;gap:8px;'>"
                f"<svg width='20' height='20' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'>"
                f"<circle cx='8' cy='14' r='4.5' stroke='#F4B400' stroke-width='2.2' fill='none'/>"
                f"<path d='M11.5 12L20 3.5' stroke='#F4B400' stroke-width='2.2' stroke-linecap='round'/>"
                f"<path d='M17 6.5L19 8.5M15.5 8L17.5 10' stroke='#F4B400' stroke-width='2.2' stroke-linecap='round'/>"
                f"</svg>"
                f"<span style='color:#1A1A1A;'>Defina sua senha</span>"
                f"</p>"
                f"<p style='font-size:0.82rem;color:#6B7280;margin:0.3rem 0 0;'>"
                f"Olá, <b>{user['nome']}</b>! Este é seu primeiro acesso."
                f"</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

            with st.form("form_trocar_senha_obrigatoria", clear_on_submit=False):
                nova = st.text_input("Nova senha", type="password",
                                     placeholder="Mínimo 6 caracteres")
                confirma = st.text_input("Confirme a nova senha", type="password",
                                         placeholder="••••••••")
                submit = st.form_submit_button("Definir senha", type="primary",
                                               use_container_width=True)

                if submit:
                    if not nova or not confirma:
                        st.error("Preencha os dois campos.")
                    elif nova != confirma:
                        st.error("As senhas não conferem.")
                    elif len(nova) < 6:
                        st.error("A senha precisa ter pelo menos 6 caracteres.")
                    else:
                        try:
                            sucesso, msg = trocar_senha(user["email"], nova)
                            if sucesso:
                                st.session_state["usuario_logado"]["precisa_trocar_senha"] = False
                                registrar_log(user["email"], "trocou_senha")
                                st.success("Senha definida com sucesso! Redirecionando...")
                                st.rerun()
                            else:
                                st.error(msg)
                        except Exception as e:
                            st.error(f"Erro: {e}")

    # Rodapé com crédito do desenvolvedor
    st.markdown(
        "<div style='text-align:center;margin-top:3rem;padding-top:1.5rem;"
        "border-top:1px solid #E5E7EB;'>"
        "<p style='font-size:12px;color:#6B7280;margin:0;'>"
        "Desenvolvido por "
        "<a href='https://www.linkedin.com/in/eng-agro-andre-ferreira/' "
        "target='_blank' rel='noopener noreferrer' "
        "style='color:#27AE60;text-decoration:none;font-weight:600;'>"
        "Andre Ferreira</a>"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.stop()


def requer_login():
    """
    Bloqueia o acesso à página se o usuário não estiver logado.
    Também força a troca de senha no primeiro acesso.
    """
    if not esta_logado():
        _tela_login()
        return

    # Se está logado mas precisa trocar a senha, força a troca
    user = usuario_atual()
    if user.get("precisa_trocar_senha"):
        _tela_troca_senha_obrigatoria()


def _tela_login():
    """Tela de login centralizada com logo + nome do painel."""
    # Esconde sidebar e menu de páginas
    st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    .main .block-container {
        padding-top: 2rem !important;
        max-width: 100% !important;
    }
    /* Inputs menores */
    .login-card input {
        font-size: 13px !important;
        padding: 0.4rem 0.6rem !important;
    }
    /* Botão verde primário (sobrescreve o azul padrão) */
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

    # Logo da Stine no topo
    import base64
    from pathlib import Path
    BASE_DIR = Path(__file__).parent.parent
    logo_src = None
    for ext in ["png", "svg", "jpg", "jpeg"]:
        path = BASE_DIR / "assets" / f"logo.{ext}"
        if path.exists():
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            data = base64.b64encode(path.read_bytes()).decode()
            logo_src = f"data:{mime};base64,{data}"
            break

    logo_html = (
        f'<img src="{logo_src}" style="height:70px;width:auto;margin-bottom:1rem;" />'
        if logo_src else
        '<div style="font-size:2.5rem;margin-bottom:0.5rem;">🌱</div>'
    )

    # Cabeçalho com logo + nome do painel
    st.markdown(f"""
<div style="text-align:center;margin-top:3rem;margin-bottom:1.5rem;">
    {logo_html}
    <h1 style="font-size:1.4rem;font-weight:700;color:#1A1A1A;margin:0;line-height:1.3;">
        Visão Operacional: Multiplication &amp; Sales Report
    </h1>
</div>
""", unsafe_allow_html=True)

    # Card de login compacto e centralizado
    col_esq, col_meio, col_dir = st.columns([1, 1, 1])
    with col_meio:
        # Tudo dentro de um único container com borda
        with st.container(border=True):
            # Cabeçalho do card (Acesso restrito)
            st.markdown(
                "<div style='text-align:center;margin-bottom:1rem;"
                "padding-bottom:0.8rem;border-bottom:1px solid #E5E7EB;'>"
                "<p style='font-size:1rem;margin:0;font-weight:600;display:flex;align-items:center;justify-content:center;gap:8px;'>"
                "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'>"
                "<rect x='4' y='10' width='16' height='11' rx='2' fill='#F4B400'/>"
                "<path d='M7 10V7a5 5 0 0110 0v3' stroke='#1E8449' stroke-width='2.2' stroke-linecap='round'/>"
                "<circle cx='12' cy='15' r='1.5' fill='#1A1A1A'/>"
                "<rect x='11.4' y='15' width='1.2' height='3' fill='#1A1A1A'/>"
                "</svg>"
                "<span style='color:#1A1A1A;'>Acesso restrito</span>"
                "</p>"
                "<p style='font-size:0.82rem;color:#6B7280;margin:0.3rem 0 0;'>"
                "Informe suas credenciais"
                "</p>"
                "</div>",
                unsafe_allow_html=True,
            )

            # Formulário
            with st.form("form_login", clear_on_submit=False):
                email = st.text_input("Email", placeholder="seu.email@empresa.com")
                senha = st.text_input("Senha", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)

                if submit:
                    if not email or not senha:
                        st.error("Preencha email e senha.")
                    else:
                        try:
                            sucesso, msg, dados = fazer_login(email, senha)
                            if sucesso:
                                st.session_state["usuario_logado"] = dados
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        except Exception as e:
                            st.error(f"Erro ao conectar: {e}")

        # Aviso de esqueceu a senha
        st.markdown(
            "<p style='text-align:center;font-size:14px;color:#6B7280;margin-top:1.2rem;'>"
            "Esqueceu a senha? Procure o administrador."
            "</p>",
            unsafe_allow_html=True,
        )

    # Rodapé com crédito do desenvolvedor
    st.markdown(
        "<div style='text-align:center;margin-top:3rem;padding-top:1.5rem;"
        "border-top:1px solid #E5E7EB;'>"
        "<p style='font-size:12px;color:#6B7280;margin:0;'>"
        "Desenvolvido por "
        "<a href='https://www.linkedin.com/in/eng-agro-andre-ferreira/' "
        "target='_blank' rel='noopener noreferrer' "
        "style='color:#27AE60;text-decoration:none;font-weight:600;'>"
        "Andre Ferreira</a>"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.stop()
