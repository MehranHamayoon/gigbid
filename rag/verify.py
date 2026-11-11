import re


def sentences(draft):
    for line in draft.splitlines():
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line.strip()):
            if sentence:
                yield sentence


def verify_claims(draft: str, evidence: list[dict], title: str = "") -> list[dict]:
    """Use a strict extractive contract. A citation alone cannot support an invented fact."""
    result = []
    items = {row["id"]: row for row in evidence}
    for claim in sentences(draft):
        citation = re.search(r"\[([\w-]+)\]\.?$", claim)
        source = items.get(citation.group(1)) if citation else None
        if source:
            asserted = claim[:citation.start()].strip().removeprefix("Portfolio evidence: ").rstrip(".")
            excerpt = source["text"].strip().rstrip(".")
            if asserted == excerpt:
                status = "supported"
            elif asserted and asserted in excerpt:
                status = "partly_supported"
            else:
                status = "unsupported"
            result.append({"text": claim, "status": status, "evidence_id": source["id"]})
            continue
        if re.fullmatch(r"(?:Hello,|Thanks,|Thank you for your consideration\.|Best,|GigBid reviewer)", claim):
            continue
        if re.fullmatch(r"I propose to (?:validate the deliverable against agreed acceptance criteria and document the results|"
                        r"review the requirements with you and agree on acceptance criteria|"
                        r"deliver a reproducible baseline and a documented handoff)\.", claim):
            continue
        if title and claim == f"Project: {title}":
            continue
        result.append({"text": claim, "status": "unsupported", "evidence_id": None})
    return result


def filter_claims(text, checks):
    remove = {row["text"] for row in checks if row["status"] != "supported"}
    return "\n\n".join(line for line in sentences(text) if line not in remove)

