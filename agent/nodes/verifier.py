from rag.verify import filter_claims, verify_claims


def verifier(state):
    draft = dict(state["proposal_draft"])
    claims = verify_claims(draft["cover_letter"], state["evidence"], title=state["job"]["title"])
    removed = sum(claim["status"] != "supported" for claim in claims)
    if removed:
        draft["cover_letter"] = filter_claims(draft["cover_letter"], claims)
    draft["evidence_ids"] = list(dict.fromkeys(row["evidence_id"] for row in claims if row["status"] == "supported"))
    return {"proposal_draft": draft, "claim_verification": claims, "claims_removed": removed}
