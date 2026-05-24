# data/ — raw catalogue exports (local only, git-ignored)

Drop the three Excel exports here. On Windows that path is:

```
C:\Users\Lucavsf\Downloads\spare-parts-ai-backend\data\
```

Expected files (exact names from the brief):

| File | Purpose | Used for |
|------|---------|----------|
| `Анализ_продаж_за_Май_2025_г__-_Апрель_2026_г_.xlsx` | 9 099 SKUs + sales, segment (ABC/XYZ), revenue 12m | master product list |
| `Наличие_на_складе_04_05_2026.xlsx` | current warehouse stock per SKU | `qty_stock` |
| `Закуп_на_склад.xlsx` | backorders / incoming | "available to order" flag |

These are **not** simple parts lists — they are sales/stock reports with
their own column layouts. The dedicated 3-file merge importer
(`scripts/import_catalog.py`, brief step 2) is a later step and needs the
real column headers to map correctly.

**What I need from you to wire the importer:** upload the three files here,
then tell me (or I'll read) the header row of each sheet — column names
like `Артикул`, `Наименование`, `Остаток`, `Цена`, `Сегмент`, `Выручка`.

Until then the system is fully testable with seeded data:

```powershell
python -m scripts.seed_db
python -m scripts.seed_error_codes
```
