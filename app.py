import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime, date
from collections import defaultdict

# === Cálculo das datas padrão ===
today = date.today()
# Data Inicial: 15 do mês anterior
if today.month == 1:
    mes_anterior = 12
    ano_anterior = today.year - 1
else:
    mes_anterior = today.month - 1
    ano_anterior = today.year
data_inicio_padrao = date(ano_anterior, mes_anterior, 15)
# Data Final: 14 do mês atual
data_fim_padrao = date(today.year, today.month, 14)

# Configuração da página
st.set_page_config("Fechamento Mensal Relatórios ACS", layout="wide")
st.title("📊 Fechamento Mensal Relatórios ACS")

# Função de processamento principal
def processar_pdfs(uploaded_files, data_inicio, data_fim, total_familias):
    cadastros_unicos_contabilizados = defaultdict(set)
    detailed_results = []
    resultados = []
    total_geral = 0

    for uploaded_file in uploaded_files:
        with pdfplumber.open(uploaded_file) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto_completo += page.extract_text(x_tolerance=2) or ""

            match_subarea = re.search(r'Subárea\(s\):\s*(.*)', texto_completo)
            if not match_subarea:
                continue

            target_professional_name = match_subarea.group(1).strip().rstrip('.')
            linhas = texto_completo.split('\n')

            detailed_results.append(("="*80 + f"\nINÍCIO DO RELATÓRIO: {uploaded_file.name}\n" + "="*80 + "\n", "header"))

            for linha in linhas:
                status = "normal"
                match_data = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
                match_cadastro = re.match(r'^\s*(\d+)', linha)

                if match_data and match_cadastro:
                    data_visita = datetime.strptime(match_data.group(1), '%d/%m/%Y').date()
                    id_cadastro = match_cadastro.group(1)

                    if not (data_inicio <= data_visita <= data_fim):
                        status = "out_of_period"
                    elif id_cadastro in cadastros_unicos_contabilizados[target_professional_name]:
                        status = "duplicate"
                    else:
                        status = "counted"
                        cadastros_unicos_contabilizados[target_professional_name].add(id_cadastro)

                    detailed_results.append((linha + "\n", status))

    # Preparar resultados consolidados
    for prof, cadastros in cadastros_unicos_contabilizados.items():
        visitas = len(cadastros)
        total_geral += visitas
        cobertura = (visitas / total_familias) * 100 if total_familias > 0 else 0
        resultados.append({
            "Profissional": prof,
            "Famílias Únicas Visitadas": visitas,
            "Cobertura (%)": f"{cobertura:.2f}%"
        })

    if total_geral > 0:
        cobertura_geral = (total_geral / total_familias) * 100 if total_familias > 0 else 0
        resultados.append({
            "Profissional": "TOTAL GERAL",
            "Famílias Únicas Visitadas": total_geral,
            "Cobertura (%)": f"{cobertura_geral:.2f}%"
        })

    return resultados, detailed_results

# Interface Streamlit
uploaded_files = st.file_uploader("Carregar relatórios PDF", type="pdf", accept_multiple_files=True)

col1, col2, col3 = st.columns(3)
with col1:
    total_familias = st.number_input("Total de Famílias Cadastradas", min_value=1, value=1)
with col2:
    data_inicio = st.date_input(
        "Data Inicial",
        value=data_inicio_padrao,
        format="DD/MM/YYYY"
    )
with col3:
    data_fim = st.date_input(
        "Data Final",
        value=data_fim_padrao,
        format="DD/MM/YYYY"
    )

if st.button("Processar Relatórios", type="primary") and uploaded_files:
    with st.spinner("Processando relatórios..."):
        resultados, detailed_results = processar_pdfs(uploaded_files, data_inicio, data_fim, total_familias)

    if resultados:
        # Exibir tabela de resultados
        df = pd.DataFrame(resultados)
        st.dataframe(df.style.apply(
            lambda x: ['background-color: #f0f0f0; font-weight: bold']*len(x)
            if x["Profissional"] == "TOTAL GERAL" else ['']*len(x),
            axis=1
        ))

        # Visualização detalhada com cores
        with st.expander("Visualização Detalhada", expanded=False):
            st.subheader("Legenda de Cores")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("🟩 **Visitas Validas-Contabilizadas**")
            with col2:
                st.markdown("🟨 **Visitas Duplicadas**")
            with col3:
                st.markdown("🟥 **Visitas Fora do Período**")
            st.markdown("---")

            html_output = ""
            for line, status in detailed_results:
                if status == "counted":
                    html_output += f'<div style="background-color:#d4edda; padding:5px; margin:2px;">{line}</div>'
                elif status == "duplicate":
                    html_output += f'<div style="background-color:#fff3cd; padding:5px; margin:2px;">{line}</div>'
                elif status == "out_of_period":
                    html_output += f'<div style="background-color:#f8d7da; padding:5px; margin:2px;">{line}</div>'
                elif status == "header":
                    html_output += f'<div style="font-weight:bold; padding:5px; margin:2px;">{line}</div>'
                else:
                    html_output += f'<div style="padding:5px; margin:2px;">{line}</div>'

            st.markdown(html_output, unsafe_allow_html=True)
    else:
        st.warning("Nenhuma visita válida encontrada para o período selecionado.")
