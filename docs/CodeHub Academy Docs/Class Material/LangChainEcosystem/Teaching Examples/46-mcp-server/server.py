from mcp.server.fastmcp import FastMCP

mcp = FastMCP("codehub-tickets")


@mcp.tool()
def get_ticket_priority(ticket_id: str) -> str:
    """Look up a CodeHub ticket's priority level."""
    return {"T-101": "critical", "T-102": "low"}.get(ticket_id, "medium")


@mcp.prompt()
def ticket_triage_skill() -> str:
    """How to triage a CodeHub ticket."""
    return (
        "You are the CodeHub Ticket Triage Agent.\n"
        "- Use get_ticket_priority to find the ticket's priority.\n"
        "- Reply with the priority level."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
