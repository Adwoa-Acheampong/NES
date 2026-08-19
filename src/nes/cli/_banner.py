"""Startup banner — NES wordmark + tagline."""

from __future__ import annotations

# "NES" rendered in the figlet "standard" font. Stored as plain text
# (no inline Rich markup) so the backslashes in the glyphs don't collide with
# Rich's [tag] markup or Python raw-string escaping — colour is applied at
# print time via a style argument. The "standard" font renders a clearly
# readable capital J (the bottom-left \___/ hook), unlike the cramped prior
# art where the J read as an I.
_WORDMARK = (
    r"  _   _  _____  ____  ",
    r" | \ | || ____|/ ___| ",
    r" |  \| ||  _|  \___ \ ",
    r" | |\  || |___  ___) |",
    r" |_| \_||_____||____/ ",
)

_RICH_WORDMARK = (
    r"  [#ff0055]_   _  [/#ff0055][#ffaa00]_____ [/#ffaa00][#00ffaa] ____  [/#00ffaa]",
    r" [#ff0055]| \ | |[/#ff0055][#ffaa00]| ____|[/#ffaa00][#00ffaa]/ ___| [/#00ffaa]",
    r" [#ff0055]|  \| |[/#ff0055][#ffaa00]|  _|  [/#ffaa00][#00ffaa]\___ \ [/#00ffaa]",
    r" [#ff0055]| |\  |[/#ff0055][#ffaa00]| |___ [/#ffaa00][#00ffaa] ___) |[/#00ffaa]",
    r" [#ff0055]|_| \_|[/#ff0055][#ffaa00]|_____|[/#ffaa00][#00ffaa]|____/ [/#00ffaa]",
)

_TAGLINE = "Personal AI, On Personal Devices"


def print_banner(quiet: bool = False) -> None:
    """Print the NES startup banner. No-op when quiet."""
    if quiet:
        return
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        text = "\n".join(_RICH_WORDMARK) + f"\n      [cyan]{_TAGLINE}[/cyan]"
        console.print(Panel(text, expand=False, border_style="#ff00ff", style="on #4a0020"))
        console.print()
    except ImportError:
        for line in _WORDMARK:
            print(line)
        print(f"      {_TAGLINE}")
        print()
