# Spreadsheet Example

> **Agent**: `spreadsheet-agent`  
> **Capability**: Spreadsheet analysis, transformation, and data processing  
> **Level**: L1 MVP

---

## Objective

Demonstrate the spreadsheet-agent's ability to analyze spreadsheet data, perform transformations, and generate summary reports or modified spreadsheets.

---

## Input

- **File**: `data.xlsx` or `data.csv` — Raw spreadsheet data
- **Format**: Excel (.xlsx) or CSV (.csv)
- **Instructions**: `instructions.txt` — Processing instructions

### Sample Input Data (data.csv)

```csv
Date,Product,Region,Sales,Units
2024-01-15,Widget-A,North,12500,250
2024-01-16,Widget-B,South,8300,166
2024-01-17,Widget-A,East,15200,304
2024-01-18,Widget-C,North,6700,134
2024-01-19,Widget-B,West,9100,182
2024-01-20,Widget-A,South,11800,236
```

### Sample Instructions (instructions.txt)

```
1. Calculate total sales and units per product
2. Calculate total sales and units per region
3. Create a summary pivot table
4. Highlight top-performing product
5. Generate a bar chart of sales by region
```

---

## Expected Output

- **Main Output**: `artifacts/spreadsheet-report.xlsx` — Processed spreadsheet with:
  - Original data sheet
  - Product summary sheet
  - Region summary sheet
  - Pivot table sheet
  - Chart sheet

- **Report**: `artifacts/spreadsheet-analysis.md` — Text analysis with:
  - Key findings
  - Top performer identification
  - Regional breakdown
  - Recommendations

### Output Quality Criteria

- [ ] All summary sheets present
- [ ] Calculations are mathematically correct
- [ ] Pivot table reflects data accurately
- [ ] Chart is properly formatted and labeled
- [ ] Report text matches spreadsheet data

---

## Running the Example

```powershell
# Navigate to project root
cd kimi-production-grade-agent-pack

# Activate virtual environment
.venv\Scripts\activate

# Note: spreadsheet is L2 (planned); use production coordinator
kimi --agent-file agents/production-coordinator.yaml --prompt (Get-Content examples/spreadsheet-example/instructions.txt -Raw)
```

---

## Verification

```powershell
# Check output files exist
Get-ChildItem -Path 'artifacts/spreadsheet-report.xlsx'
Get-ChildItem -Path 'artifacts/spreadsheet-analysis.md'

# Verify spreadsheet contents
python -c "
import openpyxl
wb = openpyxl.load_workbook('artifacts/spreadsheet-report.xlsx')
print('Sheets:', wb.sheetnames)
for name in wb.sheetnames:
    ws = wb[name]
    print(f'  {name}: {ws.max_row} rows x {ws.max_column} cols')
"

# Verify calculations
python -c "
import openpyxl
wb = openpyxl.load_workbook('artifacts/spreadsheet-report.xlsx')
ws = wb['Product Summary']
for row in ws.iter_rows(values_only=True):
    print(row)
"```

---

## Notes

- Requires `openpyxl` for Excel processing: `pip install openpyxl`
- CSV files are automatically converted to Excel format
- Large files (>10MB) may require increased timeout
- Formulas in output are preserved as Excel formulas (not static values)
