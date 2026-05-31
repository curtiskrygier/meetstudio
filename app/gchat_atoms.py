"""
Google Chat Molecules — Reusable patterns for flight data in Google Chat cards.

This module mirrors the molecules in the a2ui-catalogue googlechat package.
For production use, import from: github.com/curtiskrygier/a2ui-catalogue/googlechat
"""

from typing import List, Dict, Any


def flight_card(flight: Dict[str, Any]) -> Dict[str, Any]:
    """Single flight card with status, route, and metrics."""
    callsign = flight.get("callsign", "—")
    company = flight.get("company", "—")
    origin = flight.get("origin", "—")
    dest = flight.get("destination", "—")
    aircraft = flight.get("aircraft", "—")
    alt = int((flight.get("altitude", 0) or 0) / 100)
    speed = int(flight.get("speed", 0) or 0)
    status = flight.get("status", "—")

    status_emoji = {
        "Descending": "🔻",
        "Approach": "📍",
        "Final": "🎯",
        "Landing": "🛬",
        "Holding": "⏳",
        "En Route": "✈️",
    }.get(status, "✈️")

    text = f"""<b>{status_emoji} {callsign}</b> • {company}
{origin} ➔ {dest} ({aircraft})
Alt: {alt}00m | Speed: {speed}kt | {status}"""

    return {"textParagraph": {"text": text}}


def flight_table(flights: List[Dict[str, Any]], title: str = "ARRIVALS BOARD") -> Dict[str, Any]:
    """Formatted ASCII table of flights with box-drawing characters."""
    lines = [f"🛬 TOULOUSE BLAGNAC (TLS) — {title}\n"]
    lines.append("╔════════════════════════════════════════════════════════════════════╗")
    lines.append("║ AIRLINE              FLT#      ROUTE        DEP      ETA      STATUS ║")
    lines.append("╠════════════════════════════════════════════════════════════════════╣")

    for flight in flights[:5]:
        airline = flight.get("company", "?")[:18].ljust(18)
        callsign = flight.get("callsign", "?")[:8].ljust(8)
        origin = flight.get("origin", "?")
        dest = flight.get("destination", "?")
        route = f"{origin}→{dest}".ljust(12)
        dep = flight.get("dep_time", "?")[:5]
        eta = flight.get("eta_time", "?")[:5] if flight.get("eta_time") else "—:—"
        status = flight.get("status", "?")[:8].ljust(8)

        line = f"║ {airline} {callsign} {route} {dep}   {eta}   {status}║"
        lines.append(line)

    lines.append("╚════════════════════════════════════════════════════════════════════╝")

    return {"textParagraph": {"text": "\n".join(lines)}}


class ArrivalsBoard:
    """Builder for complete arrivals board Google Chat cards."""

    def __init__(self, airport_name: str = "TOULOUSE BLAGNAC (TLS)", emoji: str = "🛬"):
        self.airport_name = airport_name
        self.emoji = emoji
        self.sections = []

    def add_flight_cards(self, flights: List[Dict[str, Any]]) -> "ArrivalsBoard":
        """Add flight card widgets (one per flight, limit 5)."""
        for flight in flights[:5]:
            card_widget = flight_card(flight)
            self.sections.append({"widgets": [card_widget]})
        return self

    def to_card(self) -> Dict[str, Any]:
        """Convert to Google Chat Card v2 format."""
        return {
            "header": {
                "title": f"{self.emoji} {self.airport_name}",
                "subtitle": "Real-time flight tracking • Updates every 10s"
            },
            "sections": self.sections if self.sections else [{"widgets": []}]
        }

    def to_message(self) -> Dict[str, Any]:
        """Build complete Google Chat message with cardsV2."""
        return {
            "cardsV2": [{"cardId": "1", "card": self.to_card()}]
        }


def arrivals_board(flights: List[Dict[str, Any]],
                   airport_name: str = "TOULOUSE BLAGNAC (TLS)") -> Dict[str, Any]:
    """Complete arrivals board card (shorthand)."""
    board = ArrivalsBoard(airport_name=airport_name)
    board.add_flight_cards(flights)
    return board.to_message()
