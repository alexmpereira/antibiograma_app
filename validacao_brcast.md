# 🛡️ Guia de Validação de Dados BrCAST

Como lidamos com dados clínicos sensíveis para geração de laudos de Antibiograma, a integridade dos limites extraídos pelo script (`extract_br_cast.py`) é o pilar central desta aplicação.

Sempre que a instituição BrCAST lançar um novo arquivo oficial no formato `.xlsx`, siga este manual para validar visualmente que a extração puxou os dados matemáticos (CIM e Disco) com 100% de exatidão.

## 📝 Passo a Passo da Auditoria Visual

Para a auditoria, usaremos uma amostra cirúrgica cruzando o **CSV gerado** e a **Planilha Oficial do BrCAST**.

1. **Abra o arquivo original**: Dê um duplo-clique no arquivo `Tabela-pontos-de-corte-clinico-BrCAST-XX-XX-XXXX.xlsx` pelo Excel.
2. **Abra o arquivo gerado**: Abra o `breakpoints_br_cast.csv` em um bloco de notas, Excel ou editor de código.

### Validação 1: Família Enterobacterales
- **No Excel (.xlsx):**
  - Navegue nas abas inferiores até encontrar a aba chamada **Enterobacterales**.
  - Localize a linha correspondente ao antibiótico **Ertapenem**.
  - Verifique na mesma linha os limites: 
    - Coluna `S ≤` (CIM Sensível): **0,5**
    - Coluna `R >` (CIM Resistente): **>0,5**
    - Coluna `S ≥ mm` (Halo Sensível): **23**
    - Coluna `R < mm` (Halo Resistente): **<23**
- **No CSV (.csv):**
  - Procure a linha onde `microorganismo` é `Enterobacterales` e `antibiotico` é `Ertapenem`.
  - As colunas `s_cim`, `r_cim`, `diametro_s_mm` e `diametro_r_mm` devem refletir **EXATAMENTE** os números acima, garantindo que o cabeçalho não deslocou nenhuma coluna para a direita ou esquerda.

### Validação 2: Família Staphylococcus
- **No Excel (.xlsx):**
  - Vá para a aba **Staphylococcus**.
  - Localize o antibiótico **Tetraciclina**.
  - Os valores oficiais esperados são:
    - Coluna `S ≤` (CIM Sensível): **1** (com uma nota de rodapé "1" ou letra A)
    - Coluna `R >` (CIM Resistente): **>1**
    - Coluna `S ≥ mm` (Halo Sensível): **22**
    - Coluna `R < mm` (Halo Resistente): **<22**
- **No CSV (.csv):**
  - Filtre por `microorganismo` = `Staphylococcus` e `antibiotico` = `Tetraciclina`.
  - **Atenção às Notas:** No CSV, como o texto é planificado, números ou letras anexadas ao valor como notas de rodapé (ex: `11`, `22A`) estarão visíveis colados com o valor central. Isso é **completamente normal e esperado**, o script Python de diagnóstico usa regex flexíveis (na função `parse_limit`) para ignorar letras e focar no número bruto.

### Validação 3: Ausências Controladas
- **No Excel:** Procure a aba **Pseudomonas** e localize o antibiótico **Oxacilina**. Você não irá achá-lo, ou verá que não há pontos de corte estabelecidos (células com "-").
- **No CSV:** Essa linha também não deve existir ou deve estar com as colunas em branco, evitando a geração de falsos perfis S ou R.

## 🚀 Como Executar o Teste Automatizado

Além de auditar com seus próprios olhos, deixamos um teste sensível no projeto. A qualquer momento, você pode comprovar que o arquivo `.csv` reflete a exatidão com o script:

```bash
docker compose exec app python -m unittest test_antibiograma.py
```
O framework rodará o teste `test_validacao_real_excel` que abre o seu `breakpoints_br_cast.csv` e varre matematicamente os números buscando exatamente por essas associações descritas acima. Se o teste passar e disser `OK`, sua base está 100% segura.
