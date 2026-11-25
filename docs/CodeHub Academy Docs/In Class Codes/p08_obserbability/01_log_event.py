import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ticket = {"text": "Lab WiFi is down"}
logging.info("ticket_received text=%r", ticket["text"])
team = "network" if "wifi" in ticket["text"].lower() else "helpdesk"
logging.info("ticket_classified team=%s", team)

