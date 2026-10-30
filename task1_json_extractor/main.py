from pathlib import Path
from extractor import extract_invoice

SAMPLES = Path("samples")
OUTPUTS = Path("outputs")
OUTPUTS.mkdir(exist_ok=True)

def main():
    for file in sorted(SAMPLES.glob("*.txt")):
        print(f"Processing {file.name} ...")
        text = file.read_text(encoding="utf-8")
 
        try:
            invoice = extract_invoice(text)
        except RuntimeError as err:
            print(f"  FAILED: {err}\n")
            continue
 
        out_file = OUTPUTS / f"{file.stem}.json"
        out_file.write_text(invoice.model_dump_json(indent=2), encoding="utf-8")
        print(f"  Saved {out_file}\n")

if __name__ == "__main__":
    main()


