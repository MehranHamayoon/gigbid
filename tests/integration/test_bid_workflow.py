from hashlib import sha256

import pytest

from agent.settings import ROOT, policy
from apps.api.auth.session import DEFAULTS
from gigsim.service import balance, messages, proposals, write
from mcp_servers.marketplace.server import DraftPayload, create_proposal_draft
from worker import queue
from worker.main import drain, runtime


async def test_reopen_checkpoint_and_approve_once():
    run = queue.enqueue("tenant-a", "bid", "GB-001", DEFAULTS, "plan_first")
    async with runtime() as graphs:
        await drain(graphs)
    pending = queue.get("tenant-a", run["id"])
    assert pending["status"] == "pending"
    assert pending["result"]["critique"]["revision"] == 1
    assert balance("tenant-a")["remaining"] == 100
    assert queue.approve("tenant-a", run["id"], {"action": "approve"})
    assert not queue.approve("tenant-a", run["id"], {"action": "approve"})
    async with runtime() as graphs:
        await drain(graphs)
        await drain(graphs)
    complete = queue.get("tenant-a", run["id"])
    assert complete["status"] == "complete"
    assert len(proposals("tenant-a")) == 1
    assert len(messages("tenant-a", "GB-001")) == 1
    assert balance("tenant-a")["remaining"] == 94
    assert queue.get("tenant-b", run["id"]) is None
    assert balance("tenant-b")["remaining"] == 100
    assert any(item["node"] == "dispatch" for item in queue.events("tenant-a", run["id"]))


async def test_edited_unsupported_claim_cannot_dispatch():
    run = queue.enqueue("tenant-a", "bid", "GB-001", DEFAULTS)
    async with runtime() as graphs:
        await drain(graphs)
        pending = queue.get("tenant-a", run["id"])["result"]
        draft = pending["proposal_draft"]["cover_letter"] + "\n\nI have won a Nobel Prize. [ai-1-case]"
        assert queue.approve("tenant-a", run["id"], {"action": "edit", "text": draft})
        await drain(graphs)
    blocked = queue.get("tenant-a", run["id"])
    assert blocked["status"] == "blocked"
    assert balance("tenant-a")["remaining"] == 100


async def test_degraded_marketplace_queues_and_recovers(monkeypatch):
    run = queue.enqueue("tenant-a", "bid", "GB-001", DEFAULTS)
    monkeypatch.setenv("GIGBID_MARKETPLACE_DISABLED", "1")
    async with runtime() as graphs:
        await drain(graphs)
        assert queue.get("tenant-a", run["id"])["status"] == "marketplace_unavailable"
        monkeypatch.delenv("GIGBID_MARKETPLACE_DISABLED")
        assert queue.retry("tenant-a", run["id"])
        await drain(graphs)
    assert queue.get("tenant-a", run["id"])["status"] == "pending"


async def test_unsigned_marketplace_mcp_write_rejected():
    with pytest.raises(ValueError, match="authorize"):
        await create_proposal_draft(DraftPayload(job_id="GB-001", text="Synthetic draft body.", amount=330),
                                    "tenant-a", "trace", "trace-draft-001", dry_run=False)


def test_atomic_submit_is_idempotent():
    payload = {"job_id": "GB-001", "text": "Project: Build a churn prediction baseline. Skills: classification.", "amount": 330}
    write("create_proposal_draft", "tenant", "trace", "draft", payload, False, 30)
    preview = write("submit_proposal", "tenant", "trace", "submit", payload, True, 30)
    assert preview["connects"] == 6
    assert balance("tenant")["remaining"] == 100
    first = write("submit_proposal", "tenant", "trace", "submit", payload, False, 30)
    second = write("submit_proposal", "tenant", "trace", "submit", payload, False, 30)
    assert first == second
    assert balance("tenant")["remaining"] == 94
    with pytest.raises(ValueError, match="different action"):
        write("submit_proposal", "tenant", "trace", "submit", {**payload,"amount":350}, False, 30)


async def test_local_policy_change_is_config_only(tmp_path, monkeypatch):
    original = ROOT / "data/policy_pack/local.yaml"
    before = sha256(original.read_bytes()).hexdigest()
    changed = tmp_path / "policy.yaml"
    changed.write_text(original.read_text(encoding="utf-8").replace("max_connects_per_proposal: 14", "max_connects_per_proposal: 5"), encoding="utf-8")
    monkeypatch.setenv("GIGBID_POLICY", str(changed))
    policy.cache_clear()
    try:
        run = queue.enqueue("tenant-a", "bid", "GB-001", DEFAULTS)
        async with runtime() as graphs:
            await drain(graphs)
        assert queue.get("tenant-a", run["id"])["status"] == "skip"
        assert sha256(original.read_bytes()).hexdigest() == before
    finally:
        policy.cache_clear()
