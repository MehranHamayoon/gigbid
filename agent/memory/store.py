from difflib import unified_diff

from agent.memory.promotion_rules import should_promote_style_edit


async def promote_style(store, tenant, run, original, edited):
    if not store or original == edited:
        return
    namespace = (tenant, "edit_candidates")
    shorter = len(edited) <= 0.9 * len(original)
    difference = "\n".join(unified_diff(original.splitlines(), edited.splitlines(), lineterm=""))
    await store.aput(namespace, run, {"shorter": shorter, "diff": difference[:2000]})
    recent = await store.asearch(namespace, filter={"shorter": True}, limit=10)
    if should_promote_style_edit(len(recent), shorter):
        await store.aput((tenant, "style"), "concise", {"instruction": "Prefer a shorter delivery plan."})


async def promote_outcome(store, tenant, run, category, outcome):
    if store and outcome in {"replied", "interview", "hired"}:
        await store.aput((tenant, "outcome"), run, {"category": category, "stage": outcome})
