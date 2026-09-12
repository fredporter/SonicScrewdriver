"""Rich Console theme aligned to USX design token conventions.

Maps USX semantic colors to Rich Style objects for consistent
CLI output across all SonicScrewdriver command groups.

Task: task.sonic.usx.003
Source: docs/usx-sonic-tokens.md + @udos/usx-tokens v3.0.0
"""

from rich.style import Style
from rich.theme import Theme

# -- Semantic Status Styles (snackbar-aligned) --

STATUS_SUCCESS = Style(color="#4CAF50", bold=True)   # --usx-color-success
STATUS_WARNING = Style(color="#FF9800", bold=True)   # --usx-color-warning
STATUS_ERROR   = Style(color="#F44336", bold=True)   # --usx-color-error
STATUS_INFO    = Style(color="#2196F3", bold=True)   # --usx-color-info

# -- Action Styles --

ACTION_CREATE   = Style(color="#4CAF50", bold=True)  # green bold
ACTION_DESTROY  = Style(color="#F44336", bold=True)  # red bold
ACTION_INSTALL  = Style(color="#1976D2", bold=True)  # blue bold
ACTION_DIAG     = Style(color="#2196F3", bold=True)  # cyan bold

# -- Surface Styles --

SURFACE_DEFAULT   = Style(bgcolor="#1E1E1E")          # --surface
SURFACE_ELEVATED  = Style(bgcolor="#2D2D2D")          # --surface-container
TEXT_ON_SURFACE   = Style(color="#FFFFFF")            # --usx-color-on-surface (dark)
TEXT_SUBTLE       = Style(color="#9E9E9E", dim=True)  # --border-subtle equivalent

# -- Border Colors for Panel.fit() --

BORDER_SUCCESS = "green"
BORDER_WARNING = "yellow"
BORDER_ERROR   = "red"
BORDER_INFO    = "blue"

# -- Rich Theme (for Console(theme=...)) --

SONIC_THEME = Theme({
    # Status
    "status.success": STATUS_SUCCESS,
    "status.warning": STATUS_WARNING,
    "status.error": STATUS_ERROR,
    "status.info": STATUS_INFO,
    # Actions
    "action.create": ACTION_CREATE,
    "action.destroy": ACTION_DESTROY,
    "action.install": ACTION_INSTALL,
    "action.diagnostics": ACTION_DIAG,
    # Surfaces
    "surface": SURFACE_DEFAULT,
    "surface.elevated": SURFACE_ELEVATED,
    "text.on-surface": TEXT_ON_SURFACE,
    "text.subtle": TEXT_SUBTLE,
})


def border_for_status(status: str) -> str:
    """Return the Rich border_style for a given snackbar status."""
    return {
        "success": BORDER_SUCCESS,
        "warn": BORDER_WARNING,
        "error": BORDER_ERROR,
    }.get(status, BORDER_INFO)