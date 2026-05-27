"""
pages/4_Multiplication_Report.py — Auditoria do Multiplication Report
Com filtros hierárquicos na sidebar.
"""
import io
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import aplicar_tema, secao_titulo, imagem_base64
from src.auth import requer_login, usuario_atual, logout
from src.conexao import (
    abrir_planilha,
    carregar_mapeamento,
    get_header_row,
    PLANILHAS,
    carregar_is_cooperante,
)
from src.aggrid_helper import tabela
from src.sidebar_filtros import (
    aplicar_css_filtros,
    titulo_secao,
    filtro_multiselect,
    botao_limpar,
)


st.set_page_config(
    page_title="Multiplication Report - ITS",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_tema()
requer_login()

# CSS local: botão download verde
st.markdown("""
<style>
    .stDownloadButton > button[kind="primary"] {
        background-color: #27AE60 !important;
        border-color: #27AE60 !important;
        color: #FFFFFF !important;
    }
    .stDownloadButton > button[kind="primary"]:hover {
        background-color: #1E8449 !important;
        border-color: #1E8449 !important;
    }
</style>
""", unsafe_allow_html=True)

# CSS dos filtros
aplicar_css_filtros()


# === Sidebar com info do usuário (topo) ===
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
    if st.button("Sair", use_container_width=True, key="btn_sair_top"):
        logout()
        st.rerun()


# === Header customizado com ilustração Online report-bro ===
report_img = imagem_base64("Online report-bro.png")
report_img_html = (
    f'<img src="{report_img}" style="height:200px;width:auto;" />'
    if report_img
    else '<span style="font-size:2.5rem;">📊</span>'
)

st.markdown(f"""
<div class="its-header" style="align-items:center;">
    {report_img_html}
    <div class="its-header-divider" style="height:100px;"></div>
    <div class="its-header-text">
        <h1>Multiplication Report</h1>
        <div style="font-size:20px;color:#1A1A1A;font-weight:500;margin-top:8px;">
            Rastreamento de volumes de multiplicação e isenção de royalties por filial, cooperante e tecnologia.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Carregar dados da base
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def carregar_dados_multiplication():
    """Carrega dados da aba dadosOriginais da planilha Multiplication_Report."""
    tipo = "multiplication"
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


@st.cache_data(ttl=300, show_spinner=False)
def carregar_depara_multiplication():
    """Retorna dicionário {nome_destino: nome_excel}."""
    df_map = carregar_mapeamento("multiplication")
    if df_map.empty:
        return {}
    return dict(zip(df_map["nome_destino"], df_map["nome_excel"]))


# ============================================================
# Carrega e prepara os dados
# ============================================================
try:
    with st.spinner("Carregando dados da base..."):
        df = carregar_dados_multiplication()
        depara = carregar_depara_multiplication()

    if df.empty:
        st.markdown(
            "<div style='background-color:#FEF3C7;border-left:4px solid #F59E0B;"
            "padding:12px 16px;border-radius:8px;margin:1rem 0;'>"
            "<span style='color:#92400E;font-size:14px;font-weight:500;'>"
            "Nenhum dado encontrado na base. Faça um upload primeiro na página <b>Upload</b>."
            "</span></div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # Renomeia para nomes originais (Safra, Ano Operacional, etc.)
    df_view = df.rename(columns=depara)

    # === Helper: normaliza nomes de colunas (remove espaços múltiplos) ===
    def encontrar_coluna(df_, nome_alvo):
        """Encontra uma coluna pelo nome, ignorando espaços múltiplos."""
        nome_norm = " ".join(str(nome_alvo).split())
        for c in df_.columns:
            if " ".join(str(c).split()) == nome_norm:
                return c
        return None

    def filtrar_se_existe(df_, df_full, label, nome_coluna, chave, depende_de=False):
        """
        Aplica um filtro multiselect se a coluna existe no DataFrame.
        Retorna (df_filtrado, valores_selecionados).
        """
        col_real = encontrar_coluna(df_, nome_coluna)
        if col_real is None:
            return df_, []
        valores = filtro_multiselect(
            label,
            df_[col_real].dropna().unique().tolist(),
            chave=chave,
            depende_de=depende_de,
        )
        if valores:
            df_ = df_[df_[col_real].astype(str).isin(valores)]
        return df_, valores

    # Converte "Mês de Competência" para nome do mês
    # Aceita formatos: "12/2025", "01/12/2025", "2025-12-01", etc.
    MESES_PT = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
        "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
        "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro",
    }

    def formatar_mes(valor):
        v = str(valor).strip()
        if not v or v.lower() in ("nan", "none", "nat"):
            return ""

        # Tenta formato DD/MM/AAAA (ex: "01/12/2025")
        if "/" in v:
            partes = v.split("/")
            if len(partes) == 3:
                # DD/MM/AAAA
                mes_num = partes[1].zfill(2)
                ano = partes[2]
                nome = MESES_PT.get(mes_num, mes_num)
                return f"{nome}/{ano}"
            elif len(partes) == 2:
                # MM/AAAA
                mes_num = partes[0].zfill(2)
                ano = partes[1]
                nome = MESES_PT.get(mes_num, mes_num)
                return f"{nome}/{ano}"

        # Tenta formato AAAA-MM-DD (ISO)
        if "-" in v:
            partes = v.split("-")
            if len(partes) == 3:
                # AAAA-MM-DD
                ano = partes[0]
                mes_num = partes[1].zfill(2)
                nome = MESES_PT.get(mes_num, mes_num)
                return f"{nome}/{ano}"
            elif len(partes) == 2:
                # AAAA-MM ou MM-AAAA
                if len(partes[0]) == 4:
                    # AAAA-MM
                    ano, mes_num = partes[0], partes[1].zfill(2)
                else:
                    # MM-AAAA
                    mes_num, ano = partes[0].zfill(2), partes[1]
                nome = MESES_PT.get(mes_num, mes_num)
                return f"{nome}/{ano}"

        return v

    if "Mês de Competência" in df_view.columns:
        df_view["Mês de Competência"] = df_view["Mês de Competência"].apply(formatar_mes)

    # === Padroniza textos em UPPER nas colunas descritivas (desc_*) ===
    # Identifica as colunas que originalmente eram desc_* (texto livre)
    # depara é {nome_destino: nome_excel}, então pegamos os desc_*
    cols_texto_destino = [c for c in df.columns if c.startswith("desc_")]
    cols_texto_view = [depara.get(c, c) for c in cols_texto_destino]

    for col in cols_texto_view:
        if col in df_view.columns:
            df_view[col] = df_view[col].astype(str).str.upper().str.strip()
            # Restaura strings vazias quando o valor original era nan/vazio
            df_view[col] = df_view[col].replace({"NAN": "", "NONE": "", "NAT": ""})

    # === Enriquece com a classificação É Cooperante? ===
    try:
        df_coop = carregar_is_cooperante()
        if not df_coop.empty:
            map_coop = {}
            for _, row in df_coop.iterrows():
                chave = (str(row["desc_razao_social_filial"]).strip(), str(row["desc_nome_cooperante"]).strip())
                val = str(row["cat_is_cooperante"]).strip().lower()
                if val in ["sim", "true", "1", "s"]:
                    map_coop[chave] = "Sim"
                elif val in ["nao", "não", "false", "0", "n"]:
                    map_coop[chave] = "Não"
                else:
                    map_coop[chave] = "—"

            def classificar(row):
                chave = (
                    str(row.get("Razão Social Filial", "")).strip(),
                    str(row.get("Nome do Cooperante", "")).strip(),
                )
                return map_coop.get(chave, "—")

            df_view["É Cooperante?"] = df_view.apply(classificar, axis=1)
        else:
            df_view["É Cooperante?"] = "—"
    except Exception:
        df_view["É Cooperante?"] = "—"


    # ============================================================
    # FILTROS NA SIDEBAR (hierárquicos)
    # ============================================================
    titulo_secao("FILTROS")

    # === TEMPO ===
    titulo_secao("Tempo")

    df_f, safra_sel = filtrar_se_existe(df_view, df_view, "Safra", "Safra", "safra")

    df_f, ano_sel = filtrar_se_existe(df_f, df_view, "Ano Operacional", "Ano Operacional", "ano_op", depende_de=bool(safra_sel))

    df_f, mes_sel = filtrar_se_existe(df_f, df_view, "Mês de Competência", "Mês de Competência", "mes_comp", depende_de=bool(ano_sel))


    # === TERRITÓRIO ===
    titulo_secao("Território (Filial)")

    df_f, distrito_sel = filtrar_se_existe(df_f, df_view, "RLE Distrito Filial", "RLE Distrito Filial", "distrito")

    df_f, territorio_sel = filtrar_se_existe(df_f, df_view, "RLE Território Filial", "RLE Território Filial", "territorio", depende_de=bool(distrito_sel))

    df_f, uf_sel = filtrar_se_existe(df_f, df_view, "Estado da Filial", "Estado da Filial", "uf_filial", depende_de=bool(territorio_sel))

    df_f, filial_sel = filtrar_se_existe(df_f, df_view, "Razão Social Filial", "Razão Social Filial", "filial", depende_de=bool(uf_sel))

    df_f, cooperante_sel = filtrar_se_existe(df_f, df_view, "Nome do Cooperante", "Nome do Cooperante", "cooperante", depende_de=bool(filial_sel))


    # === PLANTIO ===
    titulo_secao("Plantio")

    df_f, uf_plantio_sel = filtrar_se_existe(df_f, df_view, "UF de Plantio", "UF de Plantio", "uf_plantio")

    df_f, cidade_plantio_sel = filtrar_se_existe(df_f, df_view, "Cidade de Plantio", "Cidade de Plantio", "cidade_plantio", depende_de=bool(uf_plantio_sel))


    # === TIPO DE ÁREA ===
    titulo_secao("Tipo de Área")

    tipo_area_sel = filtro_multiselect(
        "É Cooperante?",
        ["Sim", "Não", "—"],
        chave="tipo_area",
    )
    if tipo_area_sel and "É Cooperante?" in df_f.columns:
        df_f = df_f[df_f["É Cooperante?"].isin(tipo_area_sel)]


    # === PRODUTO ===
    titulo_secao("Produto")

    df_f, tecnologia_sel = filtrar_se_existe(df_f, df_view, "Tecnologia", "Tecnologia", "tecnologia")

    df_f, produto_sel = filtrar_se_existe(df_f, df_view, "Produto", "Produto", "produto", depende_de=bool(tecnologia_sel))

    df_f, categoria_sel = filtrar_se_existe(df_f, df_view, "Categoria", "Categoria", "categoria", depende_de=bool(produto_sel))


    # === STATUS ===
    titulo_secao("Status")

    df_f, status_its_sel = filtrar_se_existe(df_f, df_view, "Status Volume Isenção - ITS", "Status Volume de Isenção - ITS", "status_its")
    df_f, status_rle_sel = filtrar_se_existe(df_f, df_view, "Status Área RLE", "Status Área RLE", "status_rle")
    df_f, status_fat_sel = filtrar_se_existe(df_f, df_view, "Status de Faturamento", "Status de Faturamento", "status_fat")


    # === Botão limpar ===
    st.sidebar.markdown("<div style='margin:1rem 0;'></div>", unsafe_allow_html=True)
    botao_limpar()


    # ============================================================
    # ÁREA PRINCIPAL: tabela filtrada
    # ============================================================
    secao_titulo(
        label="AUDITORIA",
        titulo="Ver os dados carregados",
        descricao=f"Exibindo {len(df_f):,} de {len(df_view):,} registros.".replace(",", "."),
    )

    # Aviso se tem registros não-classificados
    nao_classificados = (df_f["É Cooperante?"] == "—").sum()
    if nao_classificados > 0:
        st.markdown(
            f"<div style='background-color:#FEF3C7;border-left:4px solid #F59E0B;"
            f"padding:12px 16px;border-radius:8px;margin:0 0 1rem 0;'>"
            f"<span style='color:#92400E;font-size:14px;font-weight:500;'>"
            f"<b>{nao_classificados}</b> registro(s) com classificação pendente. "
            f"Vá em <b>Cadastros</b> para classificar."
            f"</span></div>",
            unsafe_allow_html=True,
        )

    # === Tabela com AgGrid ===
    tabela(
        df_f,
        altura=600,
        busca=True,
        filtros=True,
        paginacao=True,
        paginacao_size=50,
        key="tabela_multiplication_auditoria",
    )

    # === Botão de exportar (abaixo da tabela) ===
    st.markdown("<div style='margin:1rem 0;'></div>", unsafe_allow_html=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_f.to_excel(writer, index=False, sheet_name="Multiplication_Report")
    buffer.seek(0)

    nome_arquivo = f"Multiplication_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        st.download_button(
            label="📥 Exportar Excel",
            data=buffer,
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="exportar_multiplication",
            use_container_width=True,
            type="primary",
        )


    # ============================================================
    # RELATÓRIO ANALÍTICO (Pivot Table em HTML)
    # ============================================================
    st.markdown("<div style='margin:3rem 0 1rem;'></div>", unsafe_allow_html=True)

    secao_titulo(
        label="RELATÓRIO ANALÍTICO",
        titulo="Resumo por Filial → Cooperante → Produto",
        descricao="Totalizadores hierárquicos que respeitam os filtros aplicados na barra lateral. Clique nas linhas para expandir/colapsar.",
    )

    # Identifica colunas usando o helper (tolerante a espaços)
    col_filial = encontrar_coluna(df_f, "Razão Social Filial")
    col_coop = encontrar_coluna(df_f, "Nome do Cooperante")
    col_prod = encontrar_coluna(df_f, "Produto")
    col_area = encontrar_coluna(df_f, "Área (Ha)")
    col_vol = encontrar_coluna(df_f, "Volume (Kg)")
    col_roy = encontrar_coluna(df_f, "Royalty")

    if all([col_filial, col_coop, col_prod, col_area, col_vol, col_roy]):
        # Prepara dados numéricos
        df_calc = df_f.copy()
        df_calc["_area"] = pd.to_numeric(df_calc[col_area], errors="coerce").fillna(0)
        df_calc["_vol"] = pd.to_numeric(df_calc[col_vol], errors="coerce").fillna(0)
        df_calc["_roy"] = pd.to_numeric(df_calc[col_roy], errors="coerce").fillna(0)

        # Limpa nomes vazios
        df_calc[col_filial] = df_calc[col_filial].astype(str).str.strip()
        df_calc[col_coop] = df_calc[col_coop].astype(str).str.strip()
        df_calc[col_prod] = df_calc[col_prod].astype(str).str.strip()

        # Agrupa nos 3 níveis
        agg_prod = df_calc.groupby(
            [col_filial, col_coop, col_prod], dropna=False
        ).agg(
            qtd=("_area", "size"),
            area=("_area", "sum"),
            vol=("_vol", "sum"),
            roy=("_roy", "sum"),
        ).reset_index()

        agg_coop = df_calc.groupby(
            [col_filial, col_coop], dropna=False
        ).agg(
            qtd=("_area", "size"),
            area=("_area", "sum"),
            vol=("_vol", "sum"),
            roy=("_roy", "sum"),
        ).reset_index()

        agg_filial = df_calc.groupby(
            [col_filial], dropna=False
        ).agg(
            qtd=("_area", "size"),
            area=("_area", "sum"),
            vol=("_vol", "sum"),
            roy=("_roy", "sum"),
        ).reset_index()

        # Total geral
        total_qtd = int(df_calc["_area"].count())
        total_area = float(df_calc["_area"].sum())
        total_vol = float(df_calc["_vol"].sum())
        total_roy = float(df_calc["_roy"].sum())

        # === Funções de formatação ===
        def fmt_int(v):
            return f"{int(v):,}".replace(",", ".")

        def fmt_br(v, casas=2):
            s = f"{float(v):,.{casas}f}"
            return s.replace(",", "X").replace(".", ",").replace("X", ".")

        # === Constrói a tabela linha a linha ===
        linhas_html = []

        # Total geral
        linhas_html.append(f"""
<tr class="total-geral">
    <td>TOTAL GERAL</td>
    <td class="num">{fmt_int(total_qtd)}</td>
    <td class="num">{fmt_br(total_area)}</td>
    <td class="num">{fmt_br(total_vol)}</td>
    <td class="num">{fmt_br(total_roy)}</td>
</tr>""")

        # Itera filiais
        for _, row_f in agg_filial.sort_values(col_filial).iterrows():
            filial = row_f[col_filial] or "(sem filial)"
            filial_id = f"f_{abs(hash(filial)) % 100000}"

            # Linha da Filial (clicável)
            linhas_html.append(f"""
<tr class="lv-filial" onclick="toggleGroup('{filial_id}')">
    <td><span class="arrow" id="arr_{filial_id}">▶</span> <strong>{filial}</strong></td>
    <td class="num">{fmt_int(row_f['qtd'])}</td>
    <td class="num">{fmt_br(row_f['area'])}</td>
    <td class="num">{fmt_br(row_f['vol'])}</td>
    <td class="num">{fmt_br(row_f['roy'])}</td>
</tr>""")

            # Cooperantes dessa filial
            coops_da_filial = agg_coop[agg_coop[col_filial] == row_f[col_filial]].sort_values(col_coop)

            for _, row_c in coops_da_filial.iterrows():
                coop = row_c[col_coop] or "(sem cooperante)"
                coop_id = f"c_{abs(hash(filial + coop)) % 100000}"

                # Linha do Cooperante (clicável, escondida por padrão)
                linhas_html.append(f"""
<tr class="lv-coop child-of-{filial_id} hidden" onclick="toggleGroup('{coop_id}')">
    <td style="padding-left:32px;"><span class="arrow" id="arr_{coop_id}">▶</span> {coop}</td>
    <td class="num">{fmt_int(row_c['qtd'])}</td>
    <td class="num">{fmt_br(row_c['area'])}</td>
    <td class="num">{fmt_br(row_c['vol'])}</td>
    <td class="num">{fmt_br(row_c['roy'])}</td>
</tr>""")

                # Produtos desse cooperante
                prods = agg_prod[
                    (agg_prod[col_filial] == row_f[col_filial])
                    & (agg_prod[col_coop] == row_c[col_coop])
                ].sort_values(col_prod)

                for _, row_p in prods.iterrows():
                    prod = row_p[col_prod] or "(sem produto)"
                    linhas_html.append(f"""
<tr class="lv-prod child-of-{coop_id} child-of-{filial_id} hidden">
    <td style="padding-left:64px;">{prod}</td>
    <td class="num">{fmt_int(row_p['qtd'])}</td>
    <td class="num">{fmt_br(row_p['area'])}</td>
    <td class="num">{fmt_br(row_p['vol'])}</td>
    <td class="num">{fmt_br(row_p['roy'])}</td>
</tr>""")

        # Monta HTML final
        html = """
<style>
.pivot-its {
    width: 100%;
    border-collapse: collapse;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    overflow: hidden;
    background: #FFFFFF;
}
.pivot-its thead th {
    background: #F8FAF9;
    color: #1A1A1A;
    font-weight: 700;
    font-size: 13px;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 2px solid #27AE60;
}
.pivot-its thead th.num {
    text-align: right;
}
.pivot-its td {
    padding: 8px 12px;
    border-top: 1px solid #F1F5F4;
    color: #1A1A1A;
}
.pivot-its td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.pivot-its .arrow {
    display: inline-block;
    width: 16px;
    color: #27AE60;
    font-weight: 700;
    transition: transform 0.15s;
}
.pivot-its tr.expanded > td > .arrow {
    transform: rotate(90deg);
}
.pivot-its tr.hidden {
    display: none;
}

/* Total geral */
.pivot-its .total-geral td {
    background: #1E8449;
    color: #FFFFFF !important;
    font-weight: 700;
    font-size: 14px;
    border-top: none;
}

/* Nível 1: Filial */
.pivot-its .lv-filial > td {
    background: #E9F7EF;
    font-weight: 700;
    color: #1A1A1A;
    cursor: pointer;
}
.pivot-its .lv-filial:hover > td {
    background: #D4EFDF;
}

/* Nível 2: Cooperante */
.pivot-its .lv-coop > td {
    background: #F4FBF7;
    font-weight: 600;
    cursor: pointer;
}
.pivot-its .lv-coop:hover > td {
    background: #E9F7EF;
}

/* Nível 3: Produto */
.pivot-its .lv-prod > td {
    background: #FFFFFF;
    color: #374151;
}
</style>

<div style="overflow-x:auto;">
<table class="pivot-its">
<thead>
    <tr>
        <th>Filial / Cooperante / Produto</th>
        <th class="num">Quantidade</th>
        <th class="num">Área (Ha)</th>
        <th class="num">Volume (Kg)</th>
        <th class="num">Royalty (R$)</th>
    </tr>
</thead>
<tbody>
""" + "\n".join(linhas_html) + """
</tbody>
</table>
</div>

<script>
function toggleGroup(id) {
    const arrow = document.getElementById('arr_' + id);
    if (!arrow) return;

    // Verifica estado atual baseado no símbolo da seta
    const isOpen = arrow.textContent === '▼';

    // Filhos DIRETOS dessa linha (que têm a classe child-of-{id})
    const filhosDiretos = document.querySelectorAll('.child-of-' + id);

    if (isOpen) {
        // Fechar: esconde TUDO que é descendente
        filhosDiretos.forEach(r => {
            r.classList.add('hidden');
            // Se for um cooperante (lv-coop), também colapsa a setinha dele
            if (r.classList.contains('lv-coop')) {
                const arrowFilho = r.querySelector('.arrow');
                if (arrowFilho) arrowFilho.textContent = '▶';
            }
        });
        arrow.textContent = '▶';
    } else {
        // Abrir: mostra só filhos DIRETOS (não netos)
        // Se id é de filial -> mostra cooperantes
        // Se id é de cooperante -> mostra produtos
        const idIsFilial = id.startsWith('f_');
        const idIsCoop = id.startsWith('c_');

        filhosDiretos.forEach(r => {
            if (idIsFilial && r.classList.contains('lv-coop')) {
                r.classList.remove('hidden');
            } else if (idIsCoop && r.classList.contains('lv-prod')) {
                r.classList.remove('hidden');
            }
        });
        arrow.textContent = '▼';
    }
}
</script>
"""

        # Calcula altura estimada (cada linha ~36px + 80px de header e margin)
        num_linhas = 1 + len(agg_filial) + len(agg_coop) + len(agg_prod)
        altura_estimada = min(80 + num_linhas * 36, 800)

        import streamlit.components.v1 as components
        components.html(html, height=altura_estimada, scrolling=True)

        # Botão de exportar Excel do pivot (versão "achatada")
        st.markdown("<div style='margin:1.2rem 0;'></div>", unsafe_allow_html=True)

        df_export_pivot = agg_prod.rename(columns={
            col_filial: "Razão Social Filial",
            col_coop: "Nome do Cooperante",
            col_prod: "Produto",
            "qtd": "Quantidade",
            "area": "Área (Ha)",
            "vol": "Volume (Kg)",
            "roy": "Royalty (R$)",
        })

        buf_pivot = io.BytesIO()
        with pd.ExcelWriter(buf_pivot, engine="openpyxl") as writer:
            df_export_pivot.to_excel(writer, index=False, sheet_name="Resumo")
        buf_pivot.seek(0)

        nome_pivot = f"Multiplication_Resumo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        col_btn2, _ = st.columns([1, 4])
        with col_btn2:
            st.download_button(
                label="📥 Exportar resumo",
                data=buf_pivot,
                file_name=nome_pivot,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="exportar_pivot",
                use_container_width=True,
                type="primary",
            )
    else:
        st.caption("Algumas colunas necessárias não foram encontradas para gerar o relatório.")


    # ============================================================
    # ANÁLISE GRÁFICA — 3 perguntas de negócio (Schwabish style)
    # ============================================================
    st.markdown("<div style='margin:3rem 0 1rem;'></div>", unsafe_allow_html=True)

    # Identifica colunas
    col_prod = encontrar_coluna(df_f, "Produto")
    col_area = encontrar_coluna(df_f, "Área (Ha)")
    col_vol = encontrar_coluna(df_f, "Volume (Kg)")
    col_filial = encontrar_coluna(df_f, "Razão Social Filial")
    col_roy = encontrar_coluna(df_f, "Royalty")

    # === Funções de formatação ===
    def fmt_kg_compact(v):
        v = float(v)
        if v >= 1_000_000_000:
            return f"{v/1_000_000_000:,.2f} B".replace(",", "X").replace(".", ",").replace("X", ".")
        elif v >= 1_000_000:
            return f"{v/1_000_000:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
        elif v >= 1_000:
            return f"{v/1_000:,.0f} K".replace(",", ".")
        else:
            return f"{v:,.0f}".replace(",", ".")

    def fmt_ha(v):
        return f"{float(v):,.0f}".replace(",", ".")

    def fmt_real_compact(v):
        v = float(v)
        if v >= 1_000_000_000:
            return f"R$ {v/1_000_000_000:,.2f} B".replace(",", "X").replace(".", ",").replace("X", ".")
        elif v >= 1_000_000:
            return f"R$ {v/1_000_000:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
        elif v >= 1_000:
            return f"R$ {v/1_000:,.0f} K".replace(",", ".")
        else:
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    import plotly.graph_objects as go


    # ============================================================
    # KPIs NO TOPO (4 cards)
    # ============================================================
    secao_titulo(
        label="VISÃO GERAL",
        titulo="Números do período",
        descricao="Totais agregados respeitando os filtros aplicados na barra lateral.",
    )

    total_registros = len(df_f)
    total_area_kpi = pd.to_numeric(df_f[col_area], errors="coerce").sum() if col_area else 0
    total_vol_kpi = pd.to_numeric(df_f[col_vol], errors="coerce").sum() if col_vol else 0
    total_roy_kpi = pd.to_numeric(df_f[col_roy], errors="coerce").sum() if col_roy else 0

    kpi_html = f"""
<style>
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 1rem 0 2rem;
}}
.kpi-card {{
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-left: 4px solid #27AE60;
    border-radius: 10px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
.kpi-label {{
    font-size: 11px;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    margin: 0 0 6px;
}}
.kpi-value {{
    font-size: 28px;
    font-weight: 700;
    color: #1A1A1A;
    line-height: 1.1;
    margin: 0;
    font-family: Arial, sans-serif;
}}
.kpi-unit {{
    font-size: 14px;
    color: #6B7280;
    font-weight: 500;
    margin-left: 4px;
}}
</style>

<div class="kpi-grid">
    <div class="kpi-card">
        <p class="kpi-label">Registros</p>
        <p class="kpi-value">{fmt_ha(total_registros)}</p>
    </div>
    <div class="kpi-card">
        <p class="kpi-label">Área Total</p>
        <p class="kpi-value">{fmt_ha(total_area_kpi)}<span class="kpi-unit">ha</span></p>
    </div>
    <div class="kpi-card">
        <p class="kpi-label">Volume Total</p>
        <p class="kpi-value">{fmt_kg_compact(total_vol_kpi)}<span class="kpi-unit">Kg</span></p>
    </div>
    <div class="kpi-card">
        <p class="kpi-label">Royalty Total</p>
        <p class="kpi-value">{fmt_real_compact(total_roy_kpi)}</p>
    </div>
</div>
"""
    st.markdown(kpi_html, unsafe_allow_html=True)


    # ============================================================
    # PERGUNTA 1: Quais variedades são mais plantadas?
    # Sequência de 4 visualizações (Schwabish style)
    # ============================================================
    st.markdown("<div style='margin:2rem 0 1rem;'></div>", unsafe_allow_html=True)

    if all([col_prod, col_area, col_vol]):
        df_var = df_f.copy()
        df_var["_area"] = pd.to_numeric(df_var[col_area], errors="coerce").fillna(0)
        df_var["_vol"] = pd.to_numeric(df_var[col_vol], errors="coerce").fillna(0)
        df_var[col_prod] = df_var[col_prod].astype(str).str.strip()

        agg_var = df_var.groupby(col_prod, dropna=False).agg(
            area=("_area", "sum"),
            volume=("_vol", "sum"),
        ).reset_index()

        agg_var = agg_var[
            (agg_var[col_prod] != "")
            & (agg_var[col_prod].str.lower() != "nan")
            & ((agg_var["area"] > 0) | (agg_var["volume"] > 0))
        ]

        if not agg_var.empty:
            # Selectbox de métrica (controla TODOS os 4 gráficos)
            col_select, _ = st.columns([1, 3])
            with col_select:
                metrica_var = st.selectbox(
                    "Ver por",
                    options=["Área (Ha)", "Volume (Kg)"],
                    key="metrica_variedade",
                )

            campo_valor = "area" if metrica_var == "Área (Ha)" else "volume"
            fmt_func = fmt_ha if metrica_var == "Área (Ha)" else fmt_kg_compact
            unidade = "ha" if metrica_var == "Área (Ha)" else "Kg"

            # Insights gerais
            total_metrica = agg_var[campo_valor].sum()
            top_var = agg_var.nlargest(1, campo_valor).iloc[0]
            pct_top_var = (top_var[campo_valor] / total_metrica * 100) if total_metrica else 0
            top3 = agg_var.nlargest(3, campo_valor)
            top3_pct = (top3[campo_valor].sum() / total_metrica * 100) if total_metrica else 0
            top3_nomes = ", ".join(top3[col_prod].tolist())

            secao_titulo(
                label="ANÁLISE GRÁFICA — 1/2",
                titulo="Quais variedades são mais plantadas?",
                descricao=(
                    f"<b>{top_var[col_prod]}</b> lidera com {fmt_func(top_var[campo_valor])} {unidade} "
                    f"({pct_top_var:.0f}% do total). "
                    f"Top 3 ({top3_nomes}) concentram <b>{top3_pct:.0f}%</b>."
                ),
            )

            # Ordena descendente uma vez
            agg_var_ord = agg_var.sort_values(campo_valor, ascending=False).reset_index(drop=True)
            agg_var_ord["pct"] = (agg_var_ord[campo_valor] / total_metrica * 100) if total_metrica else 0

            # ---------- VISÃO 1: Bar chart com valor + % (Schwabish principal) ----------
            st.markdown(
                "<p style='font-size:14px;color:#1A1A1A;font-weight:600;margin:1.5rem 0 0.4rem;'>"
                "<b>Ranking detalhado</b> — valor absoluto e percentual de cada variedade"
                "</p>",
                unsafe_allow_html=True,
            )

            df_v1 = agg_var_ord.sort_values(campo_valor, ascending=True).reset_index(drop=True)
            # Top 3 estão NO FIM (sort asc)
            cores_v1 = []
            for i in range(len(df_v1)):
                if i >= len(df_v1) - 3:
                    cores_v1.append("#1E8449")
                else:
                    cores_v1.append("#D1D5DB")

            fig_v1 = go.Figure()
            fig_v1.add_trace(go.Bar(
                x=df_v1[campo_valor],
                y=df_v1[col_prod],
                orientation="h",
                marker=dict(color=cores_v1, line=dict(width=0)),
                text=[
                    f"{fmt_func(v)} {unidade}  ({p:.0f}%)"
                    for v, p in zip(df_v1[campo_valor], df_v1["pct"])
                ],
                textposition="outside",
                textfont=dict(size=13, color="#1A1A1A", family="Arial, sans-serif"),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"%{{x:,.0f}} {unidade}<br>"
                    "<extra></extra>"
                ),
                cliponaxis=False,
            ))

            altura_v1 = max(320, len(df_v1) * 32 + 80)

            fig_v1.update_layout(
                height=altura_v1,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                font=dict(family="Arial, sans-serif", size=13, color="#1A1A1A"),
                margin=dict(l=20, r=180, t=10, b=20),
                showlegend=False,
                xaxis=dict(visible=False, showgrid=False),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color="#1A1A1A", size=13),
                    automargin=True,
                ),
                bargap=0.35,
            )

            st.plotly_chart(fig_v1, use_container_width=True, config={"displayModeBar": False})

            st.markdown(
                "<p style='font-size:12px;color:#6B7280;margin-top:-0.3rem;'>"
                "<span style='display:inline-block;width:12px;height:12px;background:#1E8449;"
                "border-radius:2px;vertical-align:middle;margin-right:6px;'></span>"
                "Top 3 variedades &nbsp;&nbsp;&nbsp;"
                "<span style='display:inline-block;width:12px;height:12px;background:#D1D5DB;"
                "border-radius:2px;vertical-align:middle;margin-right:6px;'></span>"
                "Demais variedades"
                "</p>",
                unsafe_allow_html=True,
            )


            # ---------- VISÃO 2: Bar chart só percentual ----------
            st.markdown(
                "<p style='font-size:14px;color:#1A1A1A;font-weight:600;margin:2.5rem 0 0.4rem;'>"
                "<b>Distribuição percentual</b> — participação de cada variedade no total"
                "</p>",
                unsafe_allow_html=True,
            )

            df_v2 = df_v1.copy()  # mesma ordem (asc)
            cores_v2 = cores_v1.copy()

            fig_v2 = go.Figure()
            fig_v2.add_trace(go.Bar(
                x=df_v2["pct"],
                y=df_v2[col_prod],
                orientation="h",
                marker=dict(color=cores_v2, line=dict(width=0)),
                text=[f"{p:.1f}%" for p in df_v2["pct"]],
                textposition="outside",
                textfont=dict(size=13, color="#1A1A1A", family="Arial, sans-serif"),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "%{x:.1f}% do total<extra></extra>"
                ),
                cliponaxis=False,
            ))

            altura_v2 = max(320, len(df_v2) * 32 + 80)

            fig_v2.update_layout(
                height=altura_v2,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                font=dict(family="Arial, sans-serif", size=13, color="#1A1A1A"),
                margin=dict(l=20, r=100, t=10, b=20),
                showlegend=False,
                xaxis=dict(visible=False, showgrid=False),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color="#1A1A1A", size=13),
                    automargin=True,
                ),
                bargap=0.35,
            )

            st.plotly_chart(fig_v2, use_container_width=True, config={"displayModeBar": False})


            # ---------- VISÃO 3: Stacked bar (1 barra única segmentada) ----------
            st.markdown(
                "<p style='font-size:14px;color:#1A1A1A;font-weight:600;margin:2.5rem 0 0.4rem;'>"
                "<b>Visão consolidada</b> — como o total se divide em uma única faixa"
                "</p>",
                unsafe_allow_html=True,
            )

            # ---------- VISÃO 3: Bar chart de proporções (em vez de stacked) ----------
            st.markdown(
                "<p style='font-size:14px;color:#1A1A1A;font-weight:600;margin:2.5rem 0 0.4rem;'>"
                "<b>Visão consolidada</b> — como o total se divide entre as variedades"
                "</p>",
                unsafe_allow_html=True,
            )

            # Recalcula tudo do zero pra evitar problemas de ordem
            stack_data = agg_var.sort_values(campo_valor, ascending=False).reset_index(drop=True)
            stack_total = stack_data[campo_valor].sum()
            stack_data["pct"] = stack_data[campo_valor] / stack_total * 100 if stack_total > 0 else 0

            # Separa grandes (>=3%) das pequenas (Outros)
            grandes = stack_data[stack_data["pct"] >= 3.0].copy().reset_index(drop=True)
            pequenas = stack_data[stack_data["pct"] < 3.0].copy().reset_index(drop=True)

            # Lista final
            lista_segmentos = []
            for _, r in grandes.iterrows():
                lista_segmentos.append({
                    "nome": r[col_prod],
                    "valor": float(r[campo_valor]),
                    "pct": float(r["pct"]),
                })

            if not pequenas.empty:
                detalhes = ", ".join([
                    f"{r[col_prod]} {r['pct']:.1f}%"
                    for _, r in pequenas.iterrows()
                ])
                lista_segmentos.append({
                    "nome": f"Outros ({detalhes})",
                    "valor": float(pequenas[campo_valor].sum()),
                    "pct": float(pequenas["pct"].sum()),
                })

            # Inverte para o gráfico de barras horizontais (maior em cima)
            lista_segmentos_inv = list(reversed(lista_segmentos))

            # Cores: gradiente verde para os top, cinza para "Outros"
            # Os top ficam no FIM da lista invertida
            cores_v3 = []
            paleta_top = ["#1E8449", "#27AE60", "#52BE80", "#A9DFBF", "#D1FAE5", "#E9F7EF"]
            n_grandes = len([s for s in lista_segmentos_inv if not s["nome"].startswith("Outros")])

            for i, seg in enumerate(lista_segmentos_inv):
                if seg["nome"].startswith("Outros"):
                    cores_v3.append("#D1D5DB")
                else:
                    # Posição no top (do menor para o maior nos grandes)
                    pos_no_top = (n_grandes - 1) - (i if not lista_segmentos_inv[0]["nome"].startswith("Outros") else i - 1)
                    # Recalcula posição correta
                    # i é a posição na lista invertida; em ordem original seria len(lista) - 1 - i
                    pos_original = len(lista_segmentos_inv) - 1 - i
                    cores_v3.append(paleta_top[pos_original] if pos_original < len(paleta_top) else "#A9DFBF")

            fig_v3 = go.Figure()
            fig_v3.add_trace(go.Bar(
                x=[seg["pct"] for seg in lista_segmentos_inv],
                y=[seg["nome"][:50] + "..." if len(seg["nome"]) > 50 else seg["nome"] for seg in lista_segmentos_inv],
                orientation="h",
                marker=dict(color=cores_v3, line=dict(width=0)),
                text=[
                    f"{seg['pct']:.1f}%  ({fmt_func(seg['valor'])} {unidade})"
                    for seg in lista_segmentos_inv
                ],
                textposition="outside",
                textfont=dict(size=13, color="#1A1A1A", family="Arial, sans-serif"),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]:,.0f} " + unidade + "<br>"
                    "%{x:.1f}% do total<extra></extra>"
                ),
                customdata=[[seg["nome"], seg["valor"]] for seg in lista_segmentos_inv],
                cliponaxis=False,
            ))

            altura_v3 = max(280, len(lista_segmentos_inv) * 38 + 80)

            fig_v3.update_layout(
                height=altura_v3,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                font=dict(family="Arial, sans-serif", size=13, color="#1A1A1A"),
                margin=dict(l=20, r=220, t=10, b=20),
                showlegend=False,
                xaxis=dict(visible=False, showgrid=False),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color="#1A1A1A", size=12),
                    automargin=True,
                ),
                bargap=0.35,
            )

            st.plotly_chart(fig_v3, use_container_width=True, config={"displayModeBar": False})


            # ---------- VISÃO 4: Pareto (barras + curva acumulada) ----------
            st.markdown(
                "<p style='font-size:14px;color:#1A1A1A;font-weight:600;margin:2.5rem 0 0.4rem;'>"
                "<b>Análise de concentração</b> — quantas variedades concentram a maioria do total?"
                "</p>",
                unsafe_allow_html=True,
            )

            # Cumulativo
            df_v4 = agg_var_ord.copy()  # ordem descendente (maiores primeiro)
            df_v4["cum_pct"] = df_v4["pct"].cumsum()

            # Identifica em qual variedade chegou em 80%
            idx_80 = df_v4[df_v4["cum_pct"] >= 80].index.min() if (df_v4["cum_pct"] >= 80).any() else len(df_v4) - 1
            var_80 = df_v4.iloc[int(idx_80)] if pd.notna(idx_80) else None

            # Cores: barras verdes nas que estão dentro dos 80%, cinzas depois
            cores_v4 = []
            for i in range(len(df_v4)):
                if pd.notna(idx_80) and i <= idx_80:
                    cores_v4.append("#27AE60")
                else:
                    cores_v4.append("#D1D5DB")

            from plotly.subplots import make_subplots
            fig_v4 = make_subplots(specs=[[{"secondary_y": True}]])

            # Barras (eixo Y esquerdo)
            fig_v4.add_trace(
                go.Bar(
                    x=df_v4[col_prod],
                    y=df_v4[campo_valor],
                    marker=dict(color=cores_v4, line=dict(width=0)),
                    text=[fmt_func(v) for v in df_v4[campo_valor]],
                    textposition="outside",
                    textfont=dict(size=11, color="#1A1A1A", family="Arial, sans-serif"),
                    name=metrica_var,
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        f"%{{y:,.0f}} {unidade}<extra></extra>"
                    ),
                    cliponaxis=False,
                ),
                secondary_y=False,
            )

            # Linha cumulativa (eixo Y direito)
            fig_v4.add_trace(
                go.Scatter(
                    x=df_v4[col_prod],
                    y=df_v4["cum_pct"],
                    mode="lines+markers",
                    line=dict(color="#1A1A1A", width=2),
                    marker=dict(size=7, color="#1A1A1A"),
                    name="% Acumulado",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Acumulado: %{y:.1f}%<extra></extra>"
                    ),
                ),
                secondary_y=True,
            )

            # Linha de referência em 80%
            fig_v4.add_hline(
                y=80,
                line=dict(color="#7F1D1D", width=1, dash="dash"),
                annotation_text="80%",
                annotation_position="right",
                annotation=dict(font=dict(color="#7F1D1D", size=11)),
                secondary_y=True,
            )

            fig_v4.update_layout(
                height=460,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                font=dict(family="Arial, sans-serif", size=12, color="#1A1A1A"),
                margin=dict(l=20, r=60, t=20, b=120),
                showlegend=False,
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color="#1A1A1A", size=11),
                    tickangle=-45,
                ),
                bargap=0.3,
            )

            # Eixo Y esquerdo: invisível (valores estão nas barras)
            fig_v4.update_yaxes(visible=False, secondary_y=False)

            # Eixo Y direito: percentual acumulado
            fig_v4.update_yaxes(
                title=dict(text="% acumulado", font=dict(color="#1A1A1A", size=12)),
                tickfont=dict(color="#1A1A1A", size=11),
                gridcolor="#F1F5F4",
                range=[0, 105],
                ticksuffix="%",
                secondary_y=True,
            )

            st.plotly_chart(fig_v4, use_container_width=True, config={"displayModeBar": False})

            # Insight do Pareto
            if var_80 is not None and idx_80 is not None:
                qtd_para_80 = int(idx_80) + 1
                st.markdown(
                    f"<p style='font-size:12px;color:#6B7280;margin-top:-0.5rem;'>"
                    f"💡 <b>{qtd_para_80}</b> variedades concentram 80% do total. "
                    f"A linha tracejada vermelha indica o limite dos 80%."
                    f"</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Sem dados de variedade nos filtros atuais.")


    # ============================================================
    # PERGUNTA 2: Quais multiplicadores plantam mais área?
    # BARRAS HORIZONTAIS (Top N)
    # ============================================================
    st.markdown("<div style='margin:3rem 0 1rem;'></div>", unsafe_allow_html=True)

    if all([col_filial, col_area]):
        df_mult = df_f.copy()
        df_mult["_area"] = pd.to_numeric(df_mult[col_area], errors="coerce").fillna(0)
        df_mult[col_filial] = df_mult[col_filial].astype(str).str.strip()

        agg_mult = df_mult.groupby(col_filial, dropna=False)["_area"].sum().reset_index()
        agg_mult = agg_mult[
            (agg_mult[col_filial] != "")
            & (agg_mult[col_filial].str.lower() != "nan")
            & (agg_mult["_area"] > 0)
        ].sort_values("_area", ascending=False).reset_index(drop=True)

        if not agg_mult.empty:
            # Top 10 fixo (sem selectbox)
            top_n_mult = 10
            df_mult_chart = agg_mult.head(top_n_mult).copy()

            # Insights
            top_filial_row = agg_mult.iloc[0]
            total_area_mult = agg_mult["_area"].sum()
            pct_top = (top_filial_row["_area"] / total_area_mult * 100) if total_area_mult else 0
            top5_pct = (agg_mult.head(5)["_area"].sum() / total_area_mult * 100) if total_area_mult else 0

            secao_titulo(
                label="ANÁLISE GRÁFICA — 2/2",
                titulo="Quais multiplicadores plantam mais área?",
                descricao=(
                    f"<b>{top_filial_row[col_filial]}</b> lidera com {fmt_ha(top_filial_row['_area'])} ha "
                    f"({pct_top:.0f}% do total). "
                    f"Top 5 concentram <b>{top5_pct:.0f}%</b> da área plantada."
                ),
            )

            # Inverte ordem para barra horizontal (maior em cima)
            df_mult_chart = df_mult_chart.sort_values("_area", ascending=True).reset_index(drop=True)

            # Cores: top 5 (que agora estão NO FIM da lista) em verde
            cores_mult = []
            for i in range(len(df_mult_chart)):
                # Os top 5 ficam nas últimas 5 posições (sort ascending)
                if i >= len(df_mult_chart) - 5:
                    cores_mult.append("#1E8449")
                else:
                    cores_mult.append("#D1D5DB")

            fig_mult = go.Figure()
            fig_mult.add_trace(go.Bar(
                x=df_mult_chart["_area"],
                y=df_mult_chart[col_filial],
                orientation="h",
                marker=dict(color=cores_mult, line=dict(width=0)),
                text=[fmt_ha(v) + " ha" for v in df_mult_chart["_area"]],
                textposition="outside",
                textfont=dict(size=13, color="#1A1A1A", family="Arial, sans-serif"),
                hovertemplate="<b>%{y}</b><br>Área: %{x:,.0f} ha<extra></extra>",
                cliponaxis=False,
            ))

            altura_mult = max(400, len(df_mult_chart) * 32 + 100)

            fig_mult.update_layout(
                height=altura_mult,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                font=dict(family="Arial, sans-serif", size=13, color="#1A1A1A"),
                margin=dict(l=20, r=140, t=20, b=20),
                showlegend=False,
                xaxis=dict(visible=False, showgrid=False),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color="#1A1A1A", size=13),
                    automargin=True,
                ),
                bargap=0.35,
            )

            st.plotly_chart(fig_mult, use_container_width=True, config={"displayModeBar": False})

            st.markdown(
                f"<p style='font-size:12px;color:#6B7280;margin-top:0.3rem;'>"
                f"<span style='display:inline-block;width:12px;height:12px;background:#1E8449;"
                f"border-radius:2px;vertical-align:middle;margin-right:6px;'></span>"
                f"Top 5 multiplicadores &nbsp;&nbsp;&nbsp;"
                f"<span style='display:inline-block;width:12px;height:12px;background:#D1D5DB;"
                f"border-radius:2px;vertical-align:middle;margin-right:6px;'></span>"
                f"Demais "
                f"{'(' + str(len(df_mult_chart) - 5) + ')' if len(df_mult_chart) > 5 else ''}"
                f"</p>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Sem dados de multiplicador nos filtros atuais.")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
