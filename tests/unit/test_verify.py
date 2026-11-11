from rag.verify import filter_claims, verify_claims


def test_verifier_rejects_forged_evidence_and_accepts_attested_skills():
    evidence = [{"id": "case-1", "text": "Built a churn baseline.", "skills": ["Python", "classification"]}]
    draft = ("Built a churn baseline. [case-1]\n"
             "Portfolio skills: Python, classification [case-1]\n"
             "I have won a Nobel Prize. [case-1]")
    checks = verify_claims(draft, evidence)
    assert [row["status"] for row in checks] == ["supported", "supported", "unsupported"]
    assert "Nobel" not in filter_claims(draft, checks)
