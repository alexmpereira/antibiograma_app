import pandas as pd
import glob
import os

def extract_breakpoints_generic(excel_path=None, output_csv="breakpoints_br_cast.csv"):
    if not excel_path:
        # Encontra o arquivo xlsx mais recente no diretório
        files = glob.glob("*.xlsx")
        if not files:
            print("Erro: Nenhum arquivo Excel (.xlsx) do BrCAST encontrado no diretório.")
            return pd.DataFrame()
        excel_path = sorted(files)[-1]
        
    print(f"Lendo dados do arquivo oficial Excel: {excel_path}...")
    xlsx = pd.ExcelFile(excel_path)
    
    # Salva os metadados do arquivo em active_metadata.json
    import json
    import re
    match = re.search(r'(\d{2}-\d{2}-\d{4})', os.path.basename(excel_path))
    publish_date = match.group(1) if match else "15-04-2026"
    metadata = {
        "active_file": os.path.basename(excel_path),
        "publish_date": publish_date.replace("-", "/")
    }
    with open("active_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Abas que são apenas texto e não contêm tabelas de antibiograma
    ignore_sheets = [
        'Conteúdo', 'Alterações', 'Notas', 'Orientações', 'Dosagens', 
        'AIT', 'Agentes Tópicos', 'Valores de corte PK-PD',
        'B.cepacia', 'L.pneumophila'
    ]
    
    rows = []
    
    for sheet_name in xlsx.sheet_names:
        if sheet_name in ignore_sheets:
            continue
            
        df = xlsx.parse(sheet_name).dropna(how='all')
        
        # O BrCAST padroniza o cabeçalho tendo "S ≤" na segunda coluna (índice 1)
        # Pode haver leves variações de espaçamento dependendo do ano
        header_idx = -1
        for i in range(min(100, len(df))):
            val = str(df.iloc[i, 1]).strip()
            if val == 'S ≤' or val == 'S <=' or 'S' in val and '≤' in val:
                header_idx = i
                break
                
        if header_idx == -1:
            raise ValueError(f"Erro estrutural: Não foi possível identificar o cabeçalho da tabela na aba '{sheet_name}'.")
            
        # Validação estrutural rigorosa para prevenir layout shifts silenciosos
        h_row = df.iloc[header_idx]
        col_s_cim = str(h_row.iloc[1]).strip()
        col_i_cim = str(h_row.iloc[2]).strip()
        col_r_cim = str(h_row.iloc[3]).strip()
        
        # 1. Validação estrita dos títulos de CIM (comum a todas as abas)
        if not ('S' in col_s_cim and '≤' in col_s_cim) or col_i_cim != 'I' or not ('R' in col_r_cim and '>' in col_r_cim):
            raise ValueError(f"Cabeçalho de CIM inválido na aba '{sheet_name}': S='{col_s_cim}', I='{col_i_cim}', R='{col_r_cim}'")
            
        # 2. Validação estrita dos títulos de Diâmetro (se houver colunas suficientes para diâmetro)
        if len(h_row) > 8:
            col_s_dia = str(h_row.iloc[6]).strip()
            col_i_dia = str(h_row.iloc[7]).strip()
            col_r_dia = str(h_row.iloc[8]).strip()
            
            # S.maltophilia repete o cabeçalho de CIM nas colunas de diâmetro devido a regras de indisponibilidade
            is_valid_s = ('S' in col_s_dia) and ('≥' in col_s_dia or '≤' in col_s_dia)
            is_valid_i = ('I' in col_i_dia) or col_i_dia in ('nan', '', 'AIT')
            is_valid_r = ('R' in col_r_dia) and ('<' in col_r_dia or '>' in col_r_dia)
            
            if not (is_valid_s and is_valid_i and is_valid_r):
                raise ValueError(f"Cabeçalho de diâmetro de halo inválido na aba '{sheet_name}': S='{col_s_dia}', I='{col_i_dia}', R='{col_r_dia}'")
            
        df_data = df.iloc[header_idx + 1:].reset_index(drop=True)
        
        for _, row in df_data.iterrows():
            antibio = str(row.iloc[0]).strip()
            if pd.isna(row.iloc[0]) or not antibio or antibio.lower() == 'nan':
                continue
                
            # Extrai os limites (CIM e Diâmetro)
            def safe_val(idx):
                if idx < len(row):
                    val = str(row.iloc[idx]).strip()
                    return val if val != 'nan' else ''
                return ''
                
            rows.append({
                "microorganismo": sheet_name,
                "antibiotico": antibio,
                "s_cim": safe_val(1),
                "i_cim": safe_val(2),
                "r_cim": safe_val(3),
                "diametro_s_mm": safe_val(6),
                "diametro_i_mm": safe_val(7),
                "diametro_r_mm": safe_val(8),
                "notas": safe_val(10)
            })
            
    df_final = pd.DataFrame(rows)
    df_final.to_csv(output_csv, index=False)
    print(f"Extração concluída com SUCESSO! {len(df_final)} limites biológicos processados.")
    print(f"Arquivo consolidado salvo como {output_csv}")
    return df_final

if __name__ == "__main__":
    extract_breakpoints_generic()
