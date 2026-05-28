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
    
    # Abas que são apenas texto e não contêm tabelas de antibiograma
    ignore_sheets = ['Conteúdo', 'Alterações', 'Notas', 'Orientações', 'Dosagens', 'AIT', 'Agentes Tópicos', 'Valores de corte PK-PD']
    
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
            print(f"Aviso: Não foi possível identificar a estrutura da tabela na aba '{sheet_name}'. Ignorando.")
            continue
            
        # O padrão do BrCAST é: 
        # 0: Antibiótico, 1: S (CIM), 2: I (CIM), 3: R (CIM), 4: AIT, 
        # 5: Disco, 6: S (Halo), 7: I (Halo), 8: R (Halo), 9: AIT (Halo), 10: Notas
        
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
