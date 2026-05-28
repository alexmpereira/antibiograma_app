import re
import pandas as pd
from flask import Flask, render_template, request

import os
import json

CSV_FILE = 'breakpoints_br_cast.csv'

def get_active_metadata():
    """Lê os metadados do arquivo active_metadata.json caso exista."""
    if os.path.exists('active_metadata.json'):
        try:
            with open('active_metadata.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"active_file": "Tabela BrCAST", "publish_date": "Desconhecida"}

def get_df_breakpoints():
    """Lê o arquivo CSV de forma dinâmica. Garante que atualizações do extrator reflitam instantaneamente."""
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame()

def carregar_dados_da_aba(micro):
    """Carrega os dados correspondentes do CSV padronizado."""
    df_breakpoints = get_df_breakpoints()
    if df_breakpoints.empty:
        return pd.DataFrame()
    # Filtra pelo microrganismo exato
    return df_breakpoints[df_breakpoints['microorganismo'] == micro].copy()

def listar_microrganismos():
    """Retorna a lista de microrganismos disponíveis dinamicamente do CSV."""
    df_breakpoints = get_df_breakpoints()
    if df_breakpoints.empty:
        return ["Nenhum dado encontrado - Regere o CSV"]
    micros = df_breakpoints['microorganismo'].dropna().unique().tolist()
    return sorted(micros)

def listar_antibioticos(micro):
    """Retorna a lista de antibióticos do microrganismo selecionado."""
    dados = carregar_dados_da_aba(micro)
    if dados.empty or 'antibiotico' not in dados.columns:
        return []
    return sorted(dados['antibiotico'].dropna().unique())

# Função auxiliar para interpretar limites
def parse_limit(value):
    """
    Converte células de limites de diâmetro (ex.: '>=14', '<20', '18-49', '-', NaN) em float.
    Caso a célula contenha referências a notas, 'IE' (evidência insuficiente) ou não contenha dígitos, retorna None.
    Para intervalos (ex.: '18-49'), retorna o limite inferior (18).
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s in ('', '-', 'nan', 'ie', 'IE', 'eia', 'EIA'):
        return None
    # Proteção rígida contra textos explicativos ou notas clínicas interpretados como limites
    if 'nota' in s.lower():
        return None
        
    # Remove parênteses externos comumente usados para limites aproximados (ex: (20) -> 20)
    s = s.replace('(', '').replace(')', '')
    
    # Se houver hífen e começar por dígito, trata como intervalo (ex.: '18-49')
    if '-' in s and s.split('-')[0].strip().isdigit():
        return float(s.split('-')[0])
    # Procura o primeiro número na string
    match = re.search(r'\d+(?:,\d+)?', s.replace('.', ','))  # suporta vírgula como decimal
    if match:
        # substitui vírgula por ponto para float
        num_str = match.group().replace(',', '.')
        return float(num_str)
    return None

def classificar_antibiograma(diametro, s_cut, i_lower, r_cut):
    if s_cut is not None and diametro >= s_cut:
        return f"S – Sensível, dose padrão: diâmetro {diametro} mm ≥ {s_cut} mm."
    elif (i_lower is not None and s_cut is not None and
          i_lower <= diametro < s_cut):
        return f"I – Sensível, aumentando exposição: diâmetro {diametro} mm entre {i_lower} mm e {s_cut} mm."
    elif r_cut is not None and diametro < r_cut:
        return f"R – Resistente: diâmetro {diametro} mm < {r_cut} mm."
    else:
        return ("Não é possível determinar a categoria com os pontos de corte de "
                "diâmetro disponíveis para esse antibiótico.")

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    micro_list = listar_microrganismos()
    selected_micro = request.form.get('microorganismo') or micro_list[0]
    antibios = listar_antibioticos(selected_micro)
    resultado = None
    nota_clinica = None
    metadata = get_active_metadata()

    if request.method == 'POST':
        antibiotico = request.form.get('antibiotico')
        diametro_str = request.form.get('diametro')

        # só tenta classificar se o diâmetro foi informado e há antibiótico selecionado
        if diametro_str and antibiotico:
            diametro = float(diametro_str)
            tabela = carregar_dados_da_aba(selected_micro)
            linha = tabela[tabela['antibiotico'] == antibiotico]
            if not linha.empty:
                row = linha.iloc[0]
                s_cut = parse_limit(row['diametro_s_mm'])
                i_lower = parse_limit(row['diametro_i_mm'])
                r_cut = parse_limit(row['diametro_r_mm'])
                
                # Captura nota clínica associada à linha
                if pd.notna(row['notas']) and str(row['notas']).strip() != '' and str(row['notas']).strip().lower() != 'nan':
                    nota_clinica = str(row['notas']).strip()

                if s_cut is not None or r_cut is not None:
                    resultado = classificar_antibiograma(diametro, s_cut, i_lower, r_cut)
                else:
                    resultado = ("Não é possível determinar a categoria com os pontos de corte de "
                                 "diâmetro disponíveis para esse antibiótico.")
            else:
                resultado = "Antibiótico não encontrado para o microrganismo selecionado."

    return render_template(
        'index.html',
        micro_list=micro_list,
        antibios=antibios,
        selected_micro=selected_micro,
        resultado=resultado,
        nota_clinica=nota_clinica,
        publish_date=metadata.get("publish_date", "Desconhecida")
    )

if __name__ == '__main__':
    app.run(debug=True)
