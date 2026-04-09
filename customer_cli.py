import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    created_at: str | None = None

    @staticmethod
    def create(name: str, email: str | None, phone: str | None) -> "Customer":
        name = name.strip()
        if not name:
            raise ValueError("name cannot be empty")
        return Customer(
            id=str(uuid.uuid4()),
            name=name,
            email=email.strip() if email and email.strip() else None,
            phone=phone.strip() if phone and phone.strip() else None,
            created_at=_utc_now_iso(),
        )


def _default_db_path() -> Path:
    return Path(__file__).resolve().parent / "customers.json"


def _read_db(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    try:
        raw = db_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        raise ValueError("DB JSON must be a list")
    except Exception as e:
        raise RuntimeError(f"Failed to read DB at '{db_path}': {e}") from e


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    try:
        tmp_path.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def _write_db(db_path: Path, customers: list[dict[str, Any]]) -> None:
    payload = json.dumps(customers, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _atomic_write_text(db_path, payload)


def _format_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "(no customers)"

    def cell(row: dict[str, Any], col: str) -> str:
        v = row.get(col)
        return "" if v is None else str(v)

    widths = {c: max(len(c), *(len(cell(r, c)) for r in rows)) for c in columns}
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    sep = "  ".join("-" * widths[c] for c in columns)
    body = "\n".join("  ".join(cell(r, c).ljust(widths[c]) for c in columns) for r in rows)
    return f"{header}\n{sep}\n{body}"


def cmd_add(args: argparse.Namespace) -> int:
    db_path = Path(args.db).expanduser()
    customers = _read_db(db_path)

    customer = Customer.create(name=args.name, email=args.email, phone=args.phone)
    customers.append(asdict(customer))
    _write_db(db_path, customers)

    print(customer.id)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    db_path = Path(args.db).expanduser()
    customers = _read_db(db_path)

    sort_key = args.sort
    customers_sorted = sorted(customers, key=lambda c: (str(c.get(sort_key) or "")).lower())

    cols = ["id", "name", "email", "phone", "created_at"]
    if args.columns:
        cols = [c.strip() for c in args.columns.split(",") if c.strip()]

    print(_format_table(customers_sorted, cols))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    db_path = Path(args.db).expanduser()
    customers = _read_db(db_path)

    before = len(customers)
    customers = [c for c in customers if str(c.get("id")) != args.id]
    after = len(customers)

    if after == before:
        print(f"Customer id not found: {args.id}", file=sys.stderr)
        return 2

    _write_db(db_path, customers)
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    db_path = Path(args.db).expanduser()
    customers = _read_db(db_path)

    found = False
    new_name = args.name.strip() if args.name is not None else None
    new_email = args.email.strip() if args.email is not None else None

    if new_name is not None and not new_name:
        print("name cannot be empty", file=sys.stderr)
        return 2

    for c in customers:
        if str(c.get("id")) != args.id:
            continue
        found = True
        if new_name is not None:
            c["name"] = new_name
        if args.email is not None:
            c["email"] = new_email if new_email else None
        break

    if not found:
        print(f"Customer id not found: {args.id}", file=sys.stderr)
        return 2

    _write_db(db_path, customers)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="customer-cli", description="Customer management CLI (JSON-backed).")
    p.add_argument("--db", default=str(_default_db_path()), help="Path to JSON database file.")

    sub = p.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Add a customer.")
    add.add_argument("--name", required=True, help="Customer name.")
    add.add_argument("--email", default=None, help="Customer email.")
    add.add_argument("--phone", default=None, help="Customer phone.")
    add.set_defaults(func=cmd_add)

    ls = sub.add_parser("list", help="List customers.")
    ls.add_argument("--sort", default="name", choices=["name", "email", "phone", "created_at", "id"], help="Sort key.")
    ls.add_argument("--columns", default=None, help="Comma-separated columns (default: id,name,email,phone,created_at).")
    ls.set_defaults(func=cmd_list)

    rm = sub.add_parser("delete", help="Delete a customer by id.")
    rm.add_argument("--id", required=True, help="Customer id (UUID) to delete.")
    rm.set_defaults(func=cmd_delete)

    up = sub.add_parser("update", help="Update a customer by id.")
    up.add_argument("--id", required=True, help="Customer id (UUID) to update.")
    up.add_argument("--name", default=None, help="New customer name (optional).")
    up.add_argument("--email", default=None, help="New customer email (optional). Use empty string to clear.")
    up.set_defaults(func=cmd_update)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

