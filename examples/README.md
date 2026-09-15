# Examples

Runnable examples for dashforge. Each writes a Power BI project into `./out`; open the `.pbip` in
Power BI Desktop (with the PBIR preview enabled — see [docs/sources.md](../docs/sources.md)).

| File | What it shows |
|------|---------------|
| `generate_from_parquet.py` | End-to-end, offline — builds a sample Parquet file and generates from it. Needs `dashforge[lakehouse]`. |
| `generate_from_bigquery.py` | Generating from a warehouse table. Needs `dashforge[bigquery]` and credentials. |
| `generate_with_llm.py` | Letting a language model refine the design. Needs `dashforge[llm]` and a model/key. |

```bash
pip install "dashforge[lakehouse]"
python examples/generate_from_parquet.py
```
