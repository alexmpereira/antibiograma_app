import unittest
from unittest.mock import patch
import pandas as pd
import os
from app import parse_limit, classificar_antibiograma
from extract_br_cast import extract_breakpoints_generic

class TestAntibiograma(unittest.TestCase):

    def test_parse_limit(self):
        # Testa o parser de limites das tabelas
        self.assertEqual(parse_limit('>=14'), 14.0)
        self.assertEqual(parse_limit('<20'), 20.0)
        self.assertEqual(parse_limit('18-49'), 18.0)
        self.assertEqual(parse_limit('20,5'), 20.5)
        self.assertIsNone(parse_limit('-'))
        self.assertIsNone(parse_limit(''))
        self.assertIsNone(parse_limit(float('nan')))

    def test_classificar_antibiograma(self):
        # Teste de classificação Sensível (S)
        # Exemplo: S cut >= 20, R cut < 18, I_lower 18
        res_s = classificar_antibiograma(20, 20.0, 18.0, 18.0)
        self.assertIn("S – Sensível", res_s)

        # Teste de classificação Intermediário/Aumentando Exposição (I)
        res_i = classificar_antibiograma(19, 20.0, 18.0, 18.0)
        self.assertIn("I – Sensível, aumentando exposição", res_i)

        # Teste de classificação Resistente (R)
        res_r = classificar_antibiograma(17, 20.0, 18.0, 18.0)
        self.assertIn("R – Resistente", res_r)

        # Teste sem a categoria I (apenas S e R)
        # S cut >= 20, R cut < 20
        res_s_no_i = classificar_antibiograma(25, 20.0, None, 20.0)
        self.assertIn("S – Sensível", res_s_no_i)
        
        res_r_no_i = classificar_antibiograma(15, 20.0, None, 20.0)
        self.assertIn("R – Resistente", res_r_no_i)

        # Teste de parâmetros insuficientes
        res_error = classificar_antibiograma(20, None, None, None)
        self.assertIn("Não é possível determinar a categoria", res_error)

    def test_classificacao_real_pseudomonas(self):
        # Validação baseada no cenário real de Pseudomonas aeruginosa + Ciprofloxacin
        # Limites BrCAST/EUCAST aproximados: S >= 26, I = 23 a 25, R < 23
        
        # Simulando resultado para diâmetro 25 (deve ser I)
        res_i = classificar_antibiograma(25, 26.0, 23.0, 23.0)
        self.assertIn("I – Sensível", res_i)
        
        # Simulando resultado para diâmetro 20 (deve ser R)
        res_r = classificar_antibiograma(20, 26.0, 23.0, 23.0)
        self.assertIn("R – Resistente", res_r)
        
        # Simulando resultado para diâmetro 27 (deve ser S)
        res_s = classificar_antibiograma(27, 26.0, 23.0, 23.0)
        self.assertIn("S – Sensível", res_s)

    @patch('extract_br_cast.pd.ExcelFile')
    @patch('extract_br_cast.glob.glob')
    def test_extracao_excel_cirurgica(self, mock_glob, mock_excel):
        # Configura um DataFrame simulando a extração exata de uma aba do Excel BrCAST
        mock_excel_table = pd.DataFrame({
            'Agente antimicrobiano': ['Notas blabla', 'S ≤', 'Ciprofloxacin', 'Meropenem'],
            'S ≤': [None, 'S ≤', '<=0.5', '<=2'],
            'I': [None, 'I', '0.5-1', '2-8'],
            'R >': [None, 'R >', '>1', '>8'],
            'AIT': [None, 'AIT', '', ''],
            'Disco': [None, 'Disco', '', ''],
            'S ≥ mm': [None, 'S ≥ mm', '26', '24'],
            'I mm': [None, 'I mm', '23-25', '18-23'],
            'R < mm': [None, 'R < mm', '23', '18'],
            'AIT2': [None, 'AIT', '', ''],
            'Notas': [None, 'Notas', 'nota1', 'nota2']
        })
        
        # Faz o mock do ExcelFile retornar nosso mock com a sheet 'Pseudomonas'
        mock_instance = mock_excel.return_value
        mock_instance.sheet_names = ['Pseudomonas']
        mock_instance.parse.return_value = mock_excel_table
        
        # Faz o mock do glob retornar um arquivo fake
        mock_glob.return_value = ['fake_tabela.xlsx']
        
        temp_csv = 'test_temp_output.csv'
        
        # Executa a função de extração que agora retornará um DataFrame processado via Excel
        df_final = extract_breakpoints_generic(None, temp_csv)
        
        # Verifica se o arquivo CSV foi gerado com sucesso
        self.assertTrue(os.path.exists(temp_csv))
        
        # Validamos os resultados (2 antibióticos extraídos)
        self.assertEqual(len(df_final), 2)
        
        # Pega a linha do Ciprofloxacin
        cipro_row = df_final[df_final['antibiotico'] == 'Ciprofloxacin'].iloc[0]
        
        # Verifica se todas as associações de coluna funcionaram
        self.assertEqual(cipro_row['microorganismo'], 'Pseudomonas')
        self.assertEqual(cipro_row['s_cim'], '<=0.5')
        self.assertEqual(cipro_row['diametro_s_mm'], '26')
        self.assertEqual(cipro_row['diametro_r_mm'], '23')
        
        # Limpa o arquivo temporário
        if os.path.exists(temp_csv):
            os.remove(temp_csv)

    def test_validacao_real_excel(self):
        """
        Teste sensível que prova a exatidão da extração validando pontos de corte 
        reais do documento contra o CSV gerado. Para validar na planilha real, veja as 
        orientações no arquivo validacao_brcast.md.
        """
        csv_path = 'breakpoints_br_cast.csv'
        if not os.path.exists(csv_path):
            self.skipTest(f"O arquivo {csv_path} não existe. Rode a extração primeiro.")
            
        df = pd.read_csv(csv_path)
        
        # Validação 1: Enterobacterales -> Ertapenem
        # Verificando se os dados extraídos correspondem EXATAMENTE ao documento
        row_erta = df[(df['microorganismo'] == 'Enterobacterales') & (df['antibiotico'] == 'Ertapenem')]
        self.assertFalse(row_erta.empty, "Ertapenem não encontrado para Enterobacterales")
        
        s_cim = str(row_erta.iloc[0]['s_cim']).replace(',', '.')
        self.assertEqual(s_cim, '0.5', "CIM Sensível incorreto para Ertapenem")
        
        r_cim = str(row_erta.iloc[0]['r_cim']).replace(',', '.')
        self.assertTrue('>0.5' in r_cim, "CIM Resistente incorreto para Ertapenem")
        
        self.assertEqual(str(row_erta.iloc[0]['diametro_s_mm']), '23', "Halo S incorreto para Ertapenem")
        self.assertEqual(str(row_erta.iloc[0]['diametro_r_mm']), '<23', "Halo R incorreto para Ertapenem")
        
        # Validação 2: Staphylococcus -> Tetraciclina
        row_tetra = df[(df['microorganismo'] == 'Staphylococcus') & (df['antibiotico'] == 'Tetraciclina')]
        self.assertFalse(row_tetra.empty, "Tetraciclina não encontrada para Staphylococcus")
        
        # Verifica presenças parciais por causa das notas de rodapé (ex: 11, >11, 22A, <22A)
        self.assertTrue('1' in str(row_tetra.iloc[0]['s_cim']))
        self.assertTrue('>1' in str(row_tetra.iloc[0]['r_cim']))
        self.assertTrue('22' in str(row_tetra.iloc[0]['diametro_s_mm']))
        self.assertTrue('<22' in str(row_tetra.iloc[0]['diametro_r_mm']))

if __name__ == '__main__':
    unittest.main()
