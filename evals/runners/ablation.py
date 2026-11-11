from collections import defaultdict
from statistics import mean


def report(rows):
    groups = defaultdict(list)
    for row in rows:
        for slice in ("all", row["persona"], row["scenario"]):
            groups[row["variant"], slice].append(row)
    return {f"{variant}/{slice}": {"n": len(data), **{
        metric: round(mean(item[metric] for item in data), 4)
        for metric in ("recall5", "mrr", "ndcg10", "ms")}}
        for (variant, slice), data in sorted(groups.items())}
