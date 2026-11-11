"""Predeclared local tool-routing benchmark. A lexical router is not an LLM."""
import re

from rag.index.ranking import tokens

TOOLS = {
    "search_jobs": ("marketplace", ("find work", "discover projects", "search jobs", "job feed")),
    "get_job": ("marketplace", ("open posting", "inspect brief", "get job", "load listing")),
    "get_connects_balance": ("marketplace", ("remaining credits", "tokens left", "get connects balance", "available connects")),
    "get_client_history": ("marketplace", ("buyer reputation", "payment verification", "get client history", "past spend")),
    "list_messages": ("marketplace", ("incoming replies", "client inbox", "list messages", "show conversations")),
    "search_evidence": ("portfolio", ("relevant proof", "matching case studies", "search evidence", "find past work")),
    "get_case_study": ("portfolio", ("read exact excerpt", "inspect citation", "get case study", "open evidence")),
    "list_skills": ("portfolio", ("show capabilities", "inventory competencies", "list skills", "attested skills")),
    "free_calendar_slots": ("workspace", ("interview availability", "find times", "free calendar slots", "schedule options")),
    "create_email_draft": ("workspace", ("prepare email", "save unsent message", "create email draft", "compose a note")),
}


def benchmark():
    records = []
    for index, (expected, (group, examples)) in enumerate(TOOLS.items()):
        for offset, request in enumerate(examples):
            text = f"{request} for case {index * 4 + offset + 1}"
            expected_id = str(index * 4 + offset + 1)
            for profile in ("fine", "coarse", "described"):
                if profile == "coarse":
                    options = {key: " ".join(name.replace("_"," ") for name, info in TOOLS.items() if info[0] == key)
                               for key in ("marketplace", "portfolio", "workspace")}
                else:
                    options = {key: key.replace("_", " ") + (" " + " ".join(info[1]) if profile == "described" else "")
                               for key, info in TOOLS.items()}
                query = set(tokens(text))
                pick = max(options, key=lambda key: len(query.intersection(tokens(options[key]))))
                argument = re.search(r"case (\d+)$", text).group(1)
                records.append({"profile": profile, "request": text, "expected": expected,
                                "selected": pick, "tool_correct": pick == (group if profile == "coarse" else expected),
                                "argument_correct": argument == expected_id and pick == expected,
                                "input_words": len(tokens(text)) + sum(len(tokens(item)) for item in options.values())})
    return records
