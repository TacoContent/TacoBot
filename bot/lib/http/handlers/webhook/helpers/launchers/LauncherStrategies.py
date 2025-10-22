"""Platform-specific launcher deep link strategies."""

from abc import ABC, abstractmethod
from typing import Literal

# Type alias for supported launcher names
LauncherName = Literal["Microsoft Store", "Steam", "Epic Games Launcher"]


class LauncherStrategy(ABC):
    """Abstract base for platform launcher link generation."""

    @property
    @abstractmethod
    def name(self) -> LauncherName:
        """Human-readable launcher name."""
        ...

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Check if URL belongs to this platform."""
        ...

    @abstractmethod
    def build_deep_link(self, url: str) -> str:
        """Generate launcher-specific deep link."""
        ...


class MicrosoftStoreLauncher(LauncherStrategy):
    @property
    def name(self) -> Literal["Microsoft Store"]:
        return "Microsoft Store"

    def matches(self, url: str) -> bool:
        return ".microsoft.com" in url

    def build_deep_link(self, url: str) -> str:
        slug = url.replace("/?", "?").split("/")[-1].split("?")[0]
        return f"ms-windows-store://pdp?productid={slug}&mode=mini&hl=en-us&gl=US&referrer=storeforweb"


class SteamLauncher(LauncherStrategy):
    @property
    def name(self) -> Literal["Steam"]:
        return "Steam"

    def matches(self, url: str) -> bool:
        return "store.steampowered.com" in url

    def build_deep_link(self, url: str) -> str:
        return f"steam://openurl/{url}"


class EpicGamesLauncher(LauncherStrategy):
    @property
    def name(self) -> Literal["Epic Games Launcher"]:
        return "Epic Games Launcher"

    def matches(self, url: str) -> bool:
        return "epicgames.com" in url

    def build_deep_link(self, url: str) -> str:
        slug = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
        return f"com.epicgames.launcher://store/p/{slug}"
