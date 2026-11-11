"""Reduce Kaggle job records to publication-safe fixed-price summary statistics."""
import argparse
import csv
import hashlib
import io
import json
import statistics
from pathlib import Path
from zipfile import ZipFile

from agent.settings import ROOT


def aggregate(path):
    with ZipFile(path) as archive, archive.open("upwork-jobs.csv") as source:
        budgets = []
        examined = 0
        for row in csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig")):
            examined += 1
            if row["is_hourly"].casefold() in {"true", "1", "yes"}:
                continue
            try:
                amount = float(row["budget"].replace(",", "").replace("$", "").strip())
            except ValueError:
                continue
            if 40 <= amount <= 25000:
                budgets.append(amount)
    quartiles = statistics.quantiles(budgets, n=4)
    return {"dataset": "Upwork Job Postings Dataset 2024 (50K Records)", "author": "asaniczka",
            "version": 1, "license": "ODC Attribution License (ODC-By)",
            "source": "https://www.kaggle.com/datasets/asaniczka/upwork-job-postings-dataset-2024-50k-records",
            "archive_sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest(),
            "examined": examined, "fixed_price_in_range": len(budgets),
            "q1": round(quartiles[0]), "median": round(quartiles[1]), "q3": round(quartiles[2])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kaggle_archive", type=Path)
    args = parser.parse_args()
    text = json.dumps(aggregate(args.kaggle_archive), indent=2)
    (ROOT / "data/sample/market_statistics.json").write_text(text + "\n", encoding="utf-8")
    print(text)
