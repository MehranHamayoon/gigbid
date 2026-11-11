import re
from collections import Counter
from functools import lru_cache
from math import log, sqrt


@lru_cache(maxsize=32768)
def tokens(text):
    return tuple(re.findall(r"[a-z0-9][a-z0-9+#.-]*", text.casefold()))


@lru_cache(maxsize=32768)
def dense(text):
    words = tokens(text)
    surface = " ".join(words)
    features = Counter(words)
    for index in range(len(surface) - 3):
        features[surface[index:index + 4]] += 0.12
    length = sqrt(sum(weight * weight for weight in features.values())) or 1
    return {feature: weight / length for feature, weight in features.items()}


def cosine(left, right):
    return sum(weight * right.get(word, 0) for word, weight in left.items())


def body(row):
    return f'{row["title"]} {row["text"][:900]} {" ".join(row["skills"])}'


def bm25(query, docs):
    if not docs:
        return []
    bags = [Counter(tokens(body(row))) for row in docs]
    lengths = [sum(bag.values()) for bag in bags]
    average = sum(lengths) / len(docs) or 1
    scores = [0.0] * len(docs)
    for term in set(tokens(query)):
        frequency = sum(term in bag for bag in bags)
        idf = log(1 + (len(docs) - frequency + 0.5) / (frequency + 0.5))
        for index, (bag, length) in enumerate(zip(bags, lengths)):
            count = bag[term]
            scores[index] += idf * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * length / average))
    return [row for _, row in sorted(zip(scores, docs), key=lambda pair: (-pair[0], pair[1]["id"]))]


def fuse(rankings, limit):
    scores = Counter()
    rows = {}
    for ranking in rankings:
        for rank, row in enumerate(ranking, 1):
            rows[row["id"]] = row
            scores[row["id"]] += 1 / (20 + rank)
    return [rows[key] for key in sorted(rows, key=lambda key: (-scores[key], key))[:limit]]
