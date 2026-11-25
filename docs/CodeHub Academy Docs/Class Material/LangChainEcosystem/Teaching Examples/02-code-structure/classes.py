# Support ticket class with escalation: escalate() raises priority to critical

class SupportTicket:
    def __init__(self, ticket_id: str, issue: str, priority: str = "medium") -> None:
        # Initialize ticket with id, issue, priority, and status open
        self.ticket_id = ticket_id
        self.issue = issue
        self.priority = priority
        self.status = "open"

    def escalate(self) -> None:
        # Raise priority to critical
        self.priority = "critical"

    def __repr__(self) -> str:
        # Display ticket id, priority, and status
        return f"SupportTicket({self.ticket_id!r}, priority={self.priority!r}, status={self.status!r})"


if __name__ == "__main__":
    # Create ticket and escalate it
    ticket = SupportTicket("T-101", "Cannot reset password")
    ticket.escalate()
    print(ticket)
