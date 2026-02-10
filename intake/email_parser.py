"""Parse inbound email payloads and extract context."""

import re
from dataclasses import dataclass
from typing import Optional

from schemas.postmark import PostmarkInboundEmail


@dataclass
class ParsedEmail:
    """Parsed email data with extracted context."""

    sender_email: str
    sender_name: str
    message_id: str
    subject: str
    body: str
    project_location: Optional[str]
    project_type: Optional[str]
    additional_context: str


# San Diego area locations to detect
KNOWN_LOCATIONS = [
    "La Jolla",
    "Del Mar",
    "Encinitas",
    "Rancho Santa Fe",
    "Carlsbad",
    "San Diego",
    "Coronado",
    "Point Loma",
    "Pacific Beach",
    "Mission Hills",
    "Ocean Beach",
    "Mission Beach",
    "Carmel Valley",
    "Solana Beach",
    "Cardiff",
    "Leucadia",
    "Hillcrest",
    "North Park",
    "South Park",
    "University Heights",
    "Kensington",
    "Normal Heights",
    "City Heights",
    "Clairemont",
    "Mira Mesa",
    "Scripps Ranch",
    "Poway",
    "Escondido",
    "Vista",
    "Oceanside",
    "San Marcos",
]

# Project types to detect
PROJECT_TYPES = [
    "interior painting",
    "exterior painting",
    "interior",
    "exterior",
    "cabinet painting",
    "cabinet refinishing",
    "cabinets",
    "kitchen",
    "bathroom",
    "bedroom",
    "living room",
    "dining room",
    "office",
    "garage",
    "deck staining",
    "deck",
    "fence",
    "trim",
    "doors",
    "stucco",
    "drywall",
    "texture",
    "ceiling",
    "accent wall",
]


class EmailParser:
    """Parse inbound emails and extract project context."""

    def __init__(self):
        # Build regex patterns
        self.location_pattern = re.compile(
            r"\b(" + "|".join(re.escape(loc) for loc in KNOWN_LOCATIONS) + r")\b",
            re.IGNORECASE,
        )
        self.project_type_pattern = re.compile(
            r"\b(" + "|".join(re.escape(pt) for pt in PROJECT_TYPES) + r")\b",
            re.IGNORECASE,
        )

    def parse(self, email: PostmarkInboundEmail) -> ParsedEmail:
        """Parse a Postmark inbound email and extract context."""
        body = email.get_text_content()
        subject = email.Subject or ""

        # Combine subject and body for context extraction
        full_text = f"{subject}\n{body}"

        # Extract location
        location = self._extract_location(full_text)

        # Extract project type
        project_type = self._extract_project_type(full_text)

        # Clean up additional context (the body text)
        additional_context = self._clean_context(body)

        return ParsedEmail(
            sender_email=email.get_sender_email(),
            sender_name=email.get_sender_name(),
            message_id=email.MessageID,
            subject=subject,
            body=body,
            project_location=location,
            project_type=project_type,
            additional_context=additional_context,
        )

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract a San Diego location from text."""
        match = self.location_pattern.search(text)
        if match:
            # Normalize case
            found = match.group(1)
            for loc in KNOWN_LOCATIONS:
                if loc.lower() == found.lower():
                    return loc
        return None

    def _extract_project_type(self, text: str) -> Optional[str]:
        """Extract the type of painting project from text."""
        match = self.project_type_pattern.search(text)
        if match:
            found = match.group(1).lower()
            # Normalize and expand abbreviated types
            if found in ("interior", "interior painting"):
                return "interior painting"
            elif found in ("exterior", "exterior painting"):
                return "exterior painting"
            elif found in ("cabinets", "cabinet painting", "cabinet refinishing"):
                return "cabinet refinishing"
            elif found in ("deck", "deck staining"):
                return "deck staining"
            return found
        return None

    def _clean_context(self, text: str) -> str:
        """Clean up email body for use as additional context."""
        if not text:
            return ""

        lines = text.strip().split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Skip email signature markers
            if line.startswith("--") or line.startswith("___"):
                break
            # Skip common signature phrases
            if any(
                phrase in line.lower()
                for phrase in [
                    "sent from my",
                    "get outlook",
                    "best regards",
                    "thanks,",
                    "thank you,",
                    "cheers,",
                ]
            ):
                break
            cleaned_lines.append(line)

        return " ".join(cleaned_lines)[:500]  # Limit context length
