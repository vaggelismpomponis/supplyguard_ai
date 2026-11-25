from uuid import uuid4

for ticket in ["WiFi is down", "Printer is offline"]:
    root = uuid4()
    print(f"trace={root} run={root} parent=None ticket={ticket!r}")
    for step in ["classify", "assign"]:
        print(f"trace={root} run={uuid4()} parent={root} step={step}")

