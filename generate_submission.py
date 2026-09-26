"""
generate_submission.py - Generates submission.jsonl for the 30 canonical test pairs.
"""

import sys
import json
from pathlib import Path

# Ensure UTF-8 console output on Windows
sys.stdout.reconfigure(encoding="utf-8")

from composer import compose

BASE_DIR = Path(__file__).parent
EXPANDED_DIR = BASE_DIR / "expanded"
DATASET_DIR = BASE_DIR / "dataset"


def load_all_contexts():
    """Load categories, merchants, customers, and triggers."""
    categories = {}
    merchants = {}
    customers = {}
    triggers = {}

    # Load categories
    cat_dir = EXPANDED_DIR / "categories"
    if not cat_dir.exists():
        cat_dir = DATASET_DIR / "categories"
    for f in cat_dir.glob("*.json"):
        data = json.load(open(f, encoding="utf-8"))
        slug = data.get("slug", f.stem)
        categories[slug] = data

    # Load merchants
    merch_dir = EXPANDED_DIR / "merchants"
    if merch_dir.exists():
        for f in merch_dir.glob("*.json"):
            data = json.load(open(f, encoding="utf-8"))
            merchants[data["merchant_id"]] = data
    else:
        seed_m = json.load(open(DATASET_DIR / "merchants_seed.json", encoding="utf-8"))
        for m in seed_m.get("merchants", []):
            merchants[m["merchant_id"]] = m

    # Load customers
    cust_dir = EXPANDED_DIR / "customers"
    if cust_dir.exists():
        for f in cust_dir.glob("*.json"):
            data = json.load(open(f, encoding="utf-8"))
            customers[data["customer_id"]] = data
    else:
        seed_c = json.load(open(DATASET_DIR / "customers_seed.json", encoding="utf-8"))
        for c in seed_c.get("customers", []):
            customers[c["customer_id"]] = c

    # Load triggers
    trig_dir = EXPANDED_DIR / "triggers"
    if trig_dir.exists():
        for f in trig_dir.glob("*.json"):
            data = json.load(open(f, encoding="utf-8"))
            triggers[data["id"]] = data
    else:
        seed_t = json.load(open(DATASET_DIR / "triggers_seed.json", encoding="utf-8"))
        for t in seed_t.get("triggers", []):
            triggers[t["id"]] = t

    return categories, merchants, customers, triggers


def main():
    test_pairs_path = EXPANDED_DIR / "test_pairs.json"
    if not test_pairs_path.exists():
        print("Error: test_pairs.json not found!")
        return

    test_pairs_data = json.load(open(test_pairs_path, encoding="utf-8"))
    pairs = test_pairs_data.get("pairs", [])

    categories, merchants, customers, triggers = load_all_contexts()

    output_lines = []
    print(f"Generating submissions for {len(pairs)} test pairs...\n")

    for p in pairs:
        test_id = p["test_id"]
        trg_id = p["trigger_id"]
        merch_id = p["merchant_id"]
        cust_id = p.get("customer_id")

        trigger = triggers.get(trg_id)
        merchant = merchants.get(merch_id)
        customer = customers.get(cust_id) if cust_id else None

        if not merchant:
            print(f"Warning: Merchant {merch_id} not found for {test_id}")
            continue
        if not trigger:
            print(f"Warning: Trigger {trg_id} not found for {test_id}")
            continue

        cat_slug = merchant.get("category_slug", "dentists")
        category = categories.get(cat_slug, {"slug": cat_slug})

        composed = compose(category, merchant, trigger, customer)

        submission_item = {
            "test_id": test_id,
            "body": composed["body"],
            "cta": composed["cta"],
            "send_as": composed["send_as"],
            "suppression_key": composed["suppression_key"],
            "rationale": composed["rationale"]
        }

        output_lines.append(json.dumps(submission_item, ensure_ascii=False))
        print(f"[{test_id}] ({composed['send_as']}) -> {composed['body']}")

    output_file = BASE_DIR / "submission.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"\nSuccessfully generated {len(output_lines)} lines in {output_file}")


if __name__ == "__main__":
    main()
