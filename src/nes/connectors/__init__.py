"""Data source connectors for Deep Research."""

from nes.connectors._stubs import (
    Attachment,
    BaseConnector,
    Document,
    SyncStatus,
)
from nes.connectors.store import KnowledgeStore

__all__ = ["Attachment", "BaseConnector", "Document", "KnowledgeStore", "SyncStatus"]

# Auto-register built-in connectors
import nes.connectors.obsidian  # noqa: F401

try:
    import nes.connectors.gmail  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.gmail_imap  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.gdrive  # noqa: F401
except ImportError:
    pass  # httpx may not be installed

try:
    import nes.connectors.notion  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.granola  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.gcontacts  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.imessage  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.apple_notes  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.apple_music  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.apple_contacts  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.slack_connector  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.outlook  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.gcalendar  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.dropbox  # noqa: F401
except ImportError:
    pass  # httpx may not be installed

try:
    import nes.connectors.whatsapp  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.oura  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.apple_health  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.strava  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.spotify  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.google_tasks  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.weather  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.github_notifications  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.hackernews  # noqa: F401
except ImportError:
    pass

try:
    import nes.connectors.news_rss  # noqa: F401
except ImportError:
    pass
