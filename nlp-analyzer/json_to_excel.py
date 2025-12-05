import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


def load_json_or_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Loads a JSON file that can be:
    - An object with keys like {"metadata": {...}, "entries": [...]} (preferred)
    - A bare array of entries
    - A JSON Lines (JSONL/NDJSON) file (one JSON object per line)

    Returns (entries, metadata)
    """
    metadata: Dict[str, Any] = {}

    with path.open("r", encoding="utf-8") as f:
        first_chunk = f.read(4096)
        f.seek(0)
        first_non_ws = next((c for c in first_chunk if not c.isspace()), "[")

        # Heuristic: JSONL typically starts with '{' or '[' per line, but not a single valid JSON array/object overall
        # We first try to parse as standard JSON
        try:
            obj = json.load(f)
            if isinstance(obj, dict):
                # Common shape: {"metadata": {...}, "entries": [...]} or similar
                entries = obj.get("entries")
                if isinstance(entries, list):
                    metadata = {k: v for k, v in obj.items() if k != "entries"}
                    return entries, metadata
                # If dict but no entries, try to treat dict values as rows
                return [obj], metadata
            elif isinstance(obj, list):
                return obj, metadata
        except json.JSONDecodeError:
            pass

        # Fall back to JSON Lines (NDJSON)
        f.seek(0)
        entries: List[Dict[str, Any]] = []
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
                if isinstance(rec, dict):
                    entries.append(rec)
            except json.JSONDecodeError:
                # skip malformed lines
                continue

        return entries, metadata


def write_excel(entries: List[Dict[str, Any]], metadata: Dict[str, Any], out_path: Path,
                entries_sheet: str = "entries", meta_sheet: str = "metadata") -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize entries (flatten nested structures if any)
    if entries:
        df_entries = pd.json_normalize(entries)
    else:
        df_entries = pd.DataFrame()

    # Prepare metadata as 2-column key/value table if dict provided
    df_meta = None
    if isinstance(metadata, dict) and metadata:
        # If metadata contains nested dicts, keep JSON-serialized values for readability
        rows = []
        for k, v in metadata.items():
            rows.append({"key": k, "value": v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)})
        df_meta = pd.DataFrame(rows)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_entries.to_excel(writer, sheet_name=entries_sheet, index=False)
        if df_meta is not None:
            df_meta.to_excel(writer, sheet_name=meta_sheet, index=False)



def main():
    parser = argparse.ArgumentParser(description="Eksisozluk dataset JSON/JSONL -> Excel (.xlsx) dönüştürücü")
    parser.add_argument("--input", "-i", required=True, help="Girdi JSON/JSONL dosya yolu")
    parser.add_argument("--output", "-o", help="Çıktı Excel (.xlsx) dosya yolu; verilmezse input_adı.xlsx üretilir")
    parser.add_argument("--entries-sheet", default="entries", help="Kayıtların yazılacağı sheet adı (varsayılan: entries)")
    parser.add_argument("--meta-sheet", default="metadata", help="Metadata'nın yazılacağı sheet adı (varsayılan: metadata)")
    parser.add_argument("--example", action="store_true", help="Sadece kullanım örneği göster ve çık")

    args = parser.parse_args()

    if args.example:
        print("Kullanım örneği:\n"
              "python nlp-analyzer/json_to_excel.py --input eksisozluk-api-master/eksisozluk_dataset_20251129_140117.json --output eksisozluk-api-master/eksisozluk_dataset_20251129_140117.xlsx\n"
              "\nSeçenekler:\n"
              "  --entries-sheet  entries sayfası adı (varsayılan: entries)\n"
              "  --meta-sheet     metadata sayfası adı (varsayılan: metadata)\n")
        return

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"Girdi bulunamadı: {in_path}")

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = in_path.with_suffix("")
        out_path = out_path.with_name(out_path.name + ".xlsx")

    entries, metadata = load_json_or_jsonl(in_path)

    # Eğer beklenen şekil ise, sadece entries'i yazmak için metadata 'metadata' anahtarından alınabilir
    # load_json_or_jsonl zaten ayırıyor: obj = { metadata: {...}, entries: [...] }

    write_excel(entries, metadata, out_path, entries_sheet=args.entries_sheet, meta_sheet=args.meta_sheet)

    print(f"Tamamlandı: {out_path}")


if __name__ == "__main__":
    main()
