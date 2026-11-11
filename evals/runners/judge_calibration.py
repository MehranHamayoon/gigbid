import argparse
import csv
import json
from pathlib import Path


def kappa(labels):
    human = [int(row["human"]) for row in labels]
    judge = [int(row["judge"]) for row in labels]
    if len(human) < 30 or not set(human + judge) <= {0,1}:
        raise ValueError("Use at least 30 matched binary human/judge labels")
    agreement = sum(left == right for left, right in zip(human, judge)) / len(human)
    p, q = sum(human)/len(human), sum(judge)/len(judge)
    expected = p*q + (1-p)*(1-q)
    return {"n": len(human), "observed": agreement, "expected": expected,
            "kappa": (agreement-expected)/(1-expected) if expected != 1 else None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("labels", type=Path)
    args = parser.parse_args()
    with args.labels.open(newline="", encoding="utf-8") as file:
        print(json.dumps(kappa(list(csv.DictReader(file))), indent=2))
