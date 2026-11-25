# Demonstrates *args (variadic positional), **kwargs (variadic keyword), and optional parameters

# Print ticket parameters: positional, default, variadic, and keyword-only
def build_ticket_summary(
    ticketid: str,
    issues: str,
    priority: str = "medium",
    *tags: str,
    assignee: str | None = None,
    **metadata: str,
) -> None:

    # Handle optional assignee (str | None union type)
    assignee_name = assignee if assignee is not None else "unassigned"

    # Display all argument types
    print(f"Ticket ID : {ticketid}")
    print(f"Issues    : {issues}")
    print(f"Priority  : {priority}")
    print(f"Assignee  : {assignee_name}")
    print(f"Tags      : {tags}")
    print(f"Extra     : {metadata}")
    print("-" * 40)


if __name__ == "__main__":
    # Full call with *tags, **kwargs, and keyword-only param
    build_ticket_summary(
        "TCK-1042",
        "Login fails",
        "high",
        "auth",
        "prod",
        assignee="alice",
        owner="team-x",
        platform="mobile",
    )

    # Minimal call with required args only
    build_ticket_summary("TCK-1043", "Checkout crashes")
