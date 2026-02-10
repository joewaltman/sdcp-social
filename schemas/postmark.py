"""Pydantic models for Postmark webhook payloads."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class PostmarkHeader(BaseModel):
    """Email header from Postmark."""

    Name: str
    Value: str


class PostmarkAttachment(BaseModel):
    """Email attachment from Postmark inbound webhook."""

    Name: str
    Content: str  # Base64-encoded content
    ContentType: str
    ContentLength: int
    ContentID: Optional[str] = None


class PostmarkFromFull(BaseModel):
    """Full from address details."""

    Email: EmailStr
    Name: Optional[str] = ""
    MailboxHash: Optional[str] = ""


class PostmarkToFull(BaseModel):
    """Full to address details."""

    Email: EmailStr
    Name: Optional[str] = ""
    MailboxHash: Optional[str] = ""


class PostmarkInboundEmail(BaseModel):
    """Postmark inbound email webhook payload."""

    # Message identification
    MessageID: str = Field(..., description="Unique message ID from Postmark")
    MessageStream: Optional[str] = "inbound"

    # Addresses
    From: str = Field(..., description="From email address")
    FromName: Optional[str] = ""
    FromFull: Optional[PostmarkFromFull] = None
    To: str = Field(..., description="To email address")
    ToFull: Optional[list[PostmarkToFull]] = None
    Cc: Optional[str] = ""
    CcFull: Optional[list[PostmarkToFull]] = None
    Bcc: Optional[str] = ""
    BccFull: Optional[list[PostmarkToFull]] = None
    ReplyTo: Optional[str] = ""

    # Content
    Subject: Optional[str] = ""
    TextBody: Optional[str] = ""
    HtmlBody: Optional[str] = ""
    StrippedTextReply: Optional[str] = ""

    # Metadata
    Date: Optional[str] = ""
    MailboxHash: Optional[str] = ""
    Tag: Optional[str] = ""
    OriginalRecipient: Optional[str] = ""

    # Attachments
    Attachments: list[PostmarkAttachment] = Field(default_factory=list)

    # Headers
    Headers: list[PostmarkHeader] = Field(default_factory=list)

    def get_sender_email(self) -> str:
        """Extract clean sender email."""
        if self.FromFull:
            return self.FromFull.Email
        # Parse from "Name <email>" format
        if "<" in self.From and ">" in self.From:
            start = self.From.index("<") + 1
            end = self.From.index(">")
            return self.From[start:end]
        return self.From

    def get_sender_name(self) -> str:
        """Extract sender name."""
        if self.FromFull and self.FromFull.Name:
            return self.FromFull.Name
        if self.FromName:
            return self.FromName
        return ""

    def get_image_attachments(self) -> list[PostmarkAttachment]:
        """Get only image attachments."""
        image_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/heic"}
        return [
            att
            for att in self.Attachments
            if att.ContentType.lower() in image_types
        ]

    def get_text_content(self) -> str:
        """Get the text content of the email, preferring stripped reply."""
        if self.StrippedTextReply:
            return self.StrippedTextReply
        if self.TextBody:
            return self.TextBody
        return ""
