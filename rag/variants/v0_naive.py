from rag.index.ranking import body, cosine, dense


def retrieve(query, docs, k=5):
    vector = dense(query)
    return sorted(docs, key=lambda row: (-cosine(vector, dense(body(row))), row["id"]))[:k]
