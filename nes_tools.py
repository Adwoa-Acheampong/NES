from langchain_core.tools import tool
from typing import Literal

# --- 1. Social Media & LinkedIn ---
@tool
def draft_linkedin_post(topic: str, tone: Literal["professional", "thought_leadership", "casual"] = "professional") -> str:
    """Drafts a LinkedIn post based on a topic and desired tone. Returns the raw text."""
    # In production, this calls a specialized sub-agent or formats a prompt
    return f"Drafting a {tone} LinkedIn post about {topic}..."

@tool
def publish_to_social(platform: Literal["linkedin", "twitter", "facebook"], content: str, schedule_time: str = "now") -> str:
    """Publishes content to a specified social media platform. Returns the post ID."""
    # In production, this calls the LinkedIn/Twitter API via OAuth
    return f"Successfully published to {platform}."

# --- 2. Email Orchestration ---
@tool
def process_inbox(action: Literal["summarize", "categorize", "draft_reply"]) -> str:
    """Fetches unread emails and performs the specified action. Returns a structured summary or draft."""
    # In production, this connects to Gmail API (IMAP/SMTP)
    return f"Processed inbox with action: {action}."

@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Sends an email to the specified recipient. Returns success/failure status."""
    # In production, this uses SMTP or Gmail API
    return f"Email sent to {recipient}."

# --- 3. Tracking & Conversions ---
@tool
def track_conversion(campaign_name: str, metric: Literal["clicks", "signups", "sales"]) -> dict:
    """Fetches current conversion metrics for a specific digital campaign. Returns a dictionary of stats."""
    # In production, this queries Google Analytics, Meta Ads, or your internal SQLite DB
    return {"campaign": campaign_name, "metric": metric, "value": 145, "delta": "+12%"}

ALL_NES_TOOLS = [
    draft_linkedin_post, publish_to_social, 
    process_inbox, send_email, 
    track_conversion
]