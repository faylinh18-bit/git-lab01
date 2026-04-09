# git-lab01
Lab01 Git

## Customer management CLI (Python)

This repo includes a small Python CLI app to manage customers in a local JSON file.

### Requirements

- Python 3.10+ installed and available as `python`

### Usage

All commands support `--db` to choose where the JSON file lives (defaults to `customers.json` next to `customer_cli.py`).

Add a customer (prints the generated customer id):

```bash
python customer_cli.py add --name "Ada Lovelace" --email "ada@example.com" --phone "+1-555-0100"
```

List customers:

```bash
python customer_cli.py list
```

Delete a customer by id:

```bash
python customer_cli.py delete --id "<uuid>"
```

Use a custom DB path:

```bash
python customer_cli.py --db ".\data\customers.json" list
```
