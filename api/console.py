"""
Console UI
==========

Rich-based split console for HTTP and TTS logs.
"""

import asyncio
from collections import deque
from datetime import datetime
from typing import Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


class ConsoleUI:
    """Split console with HTTP logs (top) and TTS logs (bottom)"""

    def __init__(self, max_lines: int = 50):
        self.console = Console()
        self.max_lines = max_lines

        # Log buffers
        self.http_logs: deque[Text] = deque(maxlen=max_lines)
        self.tts_logs: deque[Text] = deque(maxlen=max_lines)

        # Live display
        self._live: Optional[Live] = None
        self._running = False

    def _make_layout(self) -> Layout:
        """Create the split layout"""
        layout = Layout()
        layout.split_column(
            Layout(name="http", ratio=1),
            Layout(name="tts", ratio=1),
        )

        # HTTP panel
        http_content = Group(*self.http_logs) if self.http_logs else Text("No HTTP requests yet", style="dim")
        layout["http"].update(
            Panel(
                http_content,
                title="[bold cyan]HTTP Requests[/bold cyan]",
                border_style="cyan",
            )
        )

        # TTS panel
        tts_content = Group(*self.tts_logs) if self.tts_logs else Text("No TTS jobs yet", style="dim")
        layout["tts"].update(
            Panel(
                tts_content,
                title="[bold green]TTS Generation[/bold green]",
                border_style="green",
            )
        )

        return layout

    def log_http(
        self,
        method: str,
        path: str,
        status: int,
        duration_ms: float,
        request_id: str = "",
        response_body: str = "",
    ):
        """Log an HTTP request"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color based on status
        if status < 300:
            status_style = "green"
        elif status < 400:
            status_style = "yellow"
        else:
            status_style = "red"

        # Method colors
        method_styles = {
            "GET": "blue",
            "POST": "green",
            "PUT": "yellow",
            "DELETE": "red",
            "PATCH": "magenta",
        }
        method_style = method_styles.get(method, "white")

        line = Text()
        line.append(f"{timestamp} ", style="dim")
        line.append(f"[{request_id}] " if request_id else "", style="dim cyan")
        line.append(f"{method:7}", style=method_style)
        line.append(f" {path:40}", style="white")
        line.append(f" {status}", style=status_style)
        line.append(f" {duration_ms:>7.1f}ms", style="dim")

        self.http_logs.append(line)

        # Add response body as separate line if present
        if response_body:
            body_line = Text()
            body_line.append("         ", style="dim")  # indent
            # Truncate long responses
            display_body = response_body[:200] + "..." if len(response_body) > 200 else response_body
            body_line.append(f"→ {display_body}", style="dim white")
            self.http_logs.append(body_line)

        self._refresh()

    def log_tts(
        self,
        job_id: str,
        event: str,
        message: str = "",
        progress: Optional[float] = None,
    ):
        """Log a TTS event"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Event colors
        event_styles = {
            "created": "cyan",
            "started": "blue",
            "progress": "yellow",
            "completed": "green",
            "failed": "red",
        }
        event_style = event_styles.get(event, "white")

        line = Text()
        line.append(f"{timestamp} ", style="dim")
        line.append(f"[{job_id[:8]}] ", style="dim magenta")
        line.append(f"{event:10}", style=event_style)

        if progress is not None:
            pct = int(progress * 100)
            bar_filled = int(progress * 20)
            bar_empty = 20 - bar_filled
            line.append(" [")
            line.append("=" * bar_filled, style="green")
            line.append("-" * bar_empty, style="dim")
            line.append(f"] {pct:3}%")

        if message:
            line.append(f" {message}", style="dim")

        self.tts_logs.append(line)
        self._refresh()

    def _refresh(self):
        """Refresh the live display"""
        if self._live:
            self._live.update(self._make_layout())

    async def start(self):
        """Start the live display"""
        self._running = True
        self._live = Live(
            self._make_layout(),
            console=self.console,
            refresh_per_second=4,
            screen=True,
        )
        self._live.start()

    async def stop(self):
        """Stop the live display"""
        self._running = False
        if self._live:
            self._live.stop()
            self._live = None


# Global instance
_console_ui: Optional[ConsoleUI] = None


def get_console_ui() -> Optional[ConsoleUI]:
    """Get the global console UI instance"""
    return _console_ui


def set_console_ui(ui: ConsoleUI):
    """Set the global console UI instance"""
    global _console_ui
    _console_ui = ui


def log_http(method: str, path: str, status: int, duration_ms: float, request_id: str = "", response_body: str = ""):
    """Log HTTP request to console UI"""
    if _console_ui:
        _console_ui.log_http(method, path, status, duration_ms, request_id, response_body)


def log_tts(job_id: str, event: str, message: str = "", progress: Optional[float] = None):
    """Log TTS event to console UI"""
    if _console_ui:
        _console_ui.log_tts(job_id, event, message, progress)
