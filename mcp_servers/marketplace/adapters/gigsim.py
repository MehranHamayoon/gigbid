import os

import httpx

from gigsim import service


class GigSimAdapter:
    async def read(self, tool, arguments):
        endpoint = os.getenv("GIGSIM_BASE_URL")
        if endpoint:
            async with httpx.AsyncClient(base_url=endpoint, timeout=8) as client:
                result = await client.post(f"/read/{tool}", json=arguments,
                                           headers={"Authorization": f"Bearer {os.environ['GIGBID_INTERNAL_TOKEN']}"})
                result.raise_for_status()
                return result.json()
        return read_local(tool, arguments)

    async def write(self, tool, arguments):
        endpoint = os.getenv("GIGSIM_BASE_URL")
        if endpoint:
            async with httpx.AsyncClient(base_url=endpoint, timeout=8) as client:
                result = await client.post(f"/write/{tool}", json=arguments,
                                           headers={"Authorization": f"Bearer {os.environ['GIGBID_INTERNAL_TOKEN']}"})
                result.raise_for_status()
                return result.json()
        return service.write(tool, **arguments)


def read_local(tool, arguments):
    match tool:
        case "search_jobs":
            return service.search(arguments.get("query", ""), arguments.get("category", ""))
        case "get_job":
            return service.JOBS[arguments["job_id"]]
        case "get_client_history":
            client = service.CLIENTS[arguments["client_id"]]
            return {key: value for key, value in client.items() if key not in {"ceiling", "preferred_skill"}}
        case "get_connects_balance":
            return service.balance(arguments["user_id"])
        case "list_messages":
            return service.messages(arguments["user_id"], arguments.get("job_id", ""))
        case "list_pipeline":
            return service.proposals(arguments["user_id"])
    raise ValueError(f"Unknown simulator read tool: {tool}")
