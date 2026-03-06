from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AppKind = Literal["ai_image", "ai_anim", "builtin_mode", "weather", "text"]


@dataclass(frozen=True)
class CatalogApp:
    id: str
    title: str
    subtitle: str
    category: str
    kind: AppKind
    icon: str
    accent: str
    prompt: str | None = None
    mode: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    featured: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        return payload


@dataclass(frozen=True)
class CatalogCollection:
    id: str
    title: str
    subtitle: str
    description: str
    app_ids: tuple[str, ...]
    accent: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["app_ids"] = list(self.app_ids)
        return payload


APPS: tuple[CatalogApp, ...] = (
    CatalogApp(
        id="hero_clock",
        title="Hero Clock",
        subtitle="Clean statement clock for the room.",
        category="Essentials",
        kind="builtin_mode",
        icon="◔",
        accent="#80cbc4",
        mode="clock_fun",
        params={"style": 2, "blink": False},
        tags=("time", "minimal", "always-on"),
        featured=True,
    ),
    CatalogApp(
        id="weather_now",
        title="Weather Now",
        subtitle="Current conditions with the firmware weather scene.",
        category="Essentials",
        kind="weather",
        icon="☁",
        accent="#7dc4ff",
        tags=("weather", "useful", "live"),
        featured=True,
    ),
    CatalogApp(
        id="focus_scroller",
        title="Focus Banner",
        subtitle="Scrolling message for heads-down work or status notes.",
        category="Essentials",
        kind="text",
        icon="✎",
        accent="#f8c56a",
        params={"speed": 5, "rainbow": False, "text": "DEEP WORK IN PROGRESS"},
        tags=("status", "message", "utility"),
    ),
    CatalogApp(
        id="signal_starfield",
        title="Signal Starfield",
        subtitle="Native warp field for idle ambient motion.",
        category="Ambient",
        kind="builtin_mode",
        icon="✦",
        accent="#7b92ff",
        mode="starfield",
        params={"speed": 4, "density": 46, "warp": True},
        tags=("ambient", "built-in", "motion"),
        featured=True,
    ),
    CatalogApp(
        id="aurora_pines",
        title="Aurora Pines",
        subtitle="Northern lights drifting over a pine ridge.",
        category="Ambient",
        kind="ai_anim",
        icon="❄",
        accent="#84ffd6",
        prompt="display an aurora shimmering above dark pines with slow drifting light and a calm winter night",
        tags=("ambient", "night", "loop"),
        featured=True,
    ),
    CatalogApp(
        id="city_rain",
        title="Neon Rain",
        subtitle="Rain sliding through a dense night alley.",
        category="Ambient",
        kind="ai_anim",
        icon="☂",
        accent="#6fb6ff",
        prompt="display heavy rain over a neon alley with reflections pulsing in puddles and subtle moving signage",
        tags=("city", "loop", "atmosphere"),
        featured=True,
    ),
    CatalogApp(
        id="koi_moon",
        title="Moonlit Koi",
        subtitle="A bright still for calmer moments.",
        category="Ambient",
        kind="ai_image",
        icon="◒",
        accent="#ff9c6b",
        prompt="display a glowing koi fish circling beneath a full moon over still black water",
        tags=("still", "ambient", "art"),
    ),
    CatalogApp(
        id="dragon_forge",
        title="Forge Dragon",
        subtitle="Looping fire-breathing dragon scene.",
        category="Fantasy",
        kind="ai_anim",
        icon="♞",
        accent="#ff7d4d",
        prompt="display a fire breathing dragon on black volcanic cliffs with rolling flame and glowing embers",
        tags=("dragon", "fire", "loop"),
        featured=True,
    ),
    CatalogApp(
        id="storm_lighthouse",
        title="Storm Lighthouse",
        subtitle="Beacon sweeping through a thunderstorm.",
        category="Fantasy",
        kind="ai_anim",
        icon="⚑",
        accent="#9bd1ff",
        prompt="display a haunted lighthouse in a thunderstorm with lightning, waves, and a rotating beam",
        tags=("storm", "loop", "cinematic"),
    ),
    CatalogApp(
        id="snow_samurai",
        title="Snow Samurai",
        subtitle="High-contrast still with strong silhouette.",
        category="Fantasy",
        kind="ai_image",
        icon="⚔",
        accent="#d6e4ff",
        prompt="display a lone samurai beneath falling snow with a glowing blade and dark pine forest",
        tags=("still", "character", "winter"),
    ),
    CatalogApp(
        id="forest_shrine",
        title="Forest Shrine",
        subtitle="Sacred lantern glow through mist.",
        category="Fantasy",
        kind="ai_image",
        icon="⌘",
        accent="#8fe28f",
        prompt="display a hidden forest shrine lit by warm lanterns and drifting green mist",
        tags=("still", "mystic", "green"),
    ),
    CatalogApp(
        id="warp_tunnel",
        title="Warp Tunnel",
        subtitle="Fast sci-fi motion that reads well on LED.",
        category="Sci-Fi",
        kind="ai_anim",
        icon="➠",
        accent="#62d4ff",
        prompt="display a spaceship entering warp speed through a bright star tunnel with strong forward motion",
        tags=("space", "loop", "motion"),
    ),
    CatalogApp(
        id="orbital_station",
        title="Orbital Station",
        subtitle="Elegant still for desk mode.",
        category="Sci-Fi",
        kind="ai_image",
        icon="◎",
        accent="#7ab6ff",
        prompt="display a glowing orbital station hanging above a blue planet with crisp silhouette and deep space backdrop",
        tags=("still", "space", "clean"),
    ),
    CatalogApp(
        id="jellyfish_bloom",
        title="Jellyfish Bloom",
        subtitle="Soft underwater drift with rich color.",
        category="Sci-Fi",
        kind="ai_anim",
        icon="◌",
        accent="#8df7ff",
        prompt="display luminous jellyfish drifting through deep ocean water with gentle pulse and trailing light",
        tags=("underwater", "loop", "ambient"),
    ),
    CatalogApp(
        id="synth_sunset",
        title="Synth Sunset",
        subtitle="Palm silhouettes and highway glow.",
        category="Retro",
        kind="ai_anim",
        icon="☼",
        accent="#ff9bd8",
        prompt="display a synthwave sunset over a glowing highway with moving scanlines and drifting palms",
        tags=("retro", "loop", "sunset"),
        featured=True,
    ),
    CatalogApp(
        id="arcade_racer",
        title="Arcade Racer",
        subtitle="Classic outrun-inspired motion scene.",
        category="Retro",
        kind="ai_anim",
        icon="▰",
        accent="#ff8f68",
        prompt="display an arcade racer speeding into a neon horizon with bold road stripes and moving lights",
        tags=("retro", "speed", "loop"),
    ),
    CatalogApp(
        id="mario_stage",
        title="Plumber Stage",
        subtitle="Retro platform tribute still.",
        category="Retro",
        kind="ai_image",
        icon="◼",
        accent="#f35c4d",
        prompt="display a retro platform hero leaping toward a question block above brick ground in clean pixel art",
        tags=("retro", "still", "game"),
    ),
    CatalogApp(
        id="metroid_core",
        title="Metroid Core",
        subtitle="Floating alien core with rich palette.",
        category="Retro",
        kind="ai_image",
        icon="⬢",
        accent="#9a8cff",
        prompt="display a glowing alien core floating in dark space with tentacles and eerie blue light",
        tags=("retro", "still", "sci-fi"),
    ),
    CatalogApp(
        id="forge_flames",
        title="Forge Flames",
        subtitle="Pure looping fire for atmospheric light.",
        category="Mood",
        kind="ai_anim",
        icon="♨",
        accent="#ff9656",
        prompt="display flames rolling across a blacksmith forge with sparks and hot orange glow",
        tags=("fire", "loop", "ambient"),
    ),
    CatalogApp(
        id="calm_rainbow",
        title="Prism Flow",
        subtitle="Native rainbow mode tuned for smoother gradient flow.",
        category="Mood",
        kind="builtin_mode",
        icon="◈",
        accent="#ffd66b",
        mode="rainbow",
        params={"speed": 3, "scale": 10, "style": 1},
        tags=("built-in", "color", "idle"),
    ),
    CatalogApp(
        id="message_board",
        title="Message Board",
        subtitle="Custom note from Goddard, Telegram, or iMessage.",
        category="Agent",
        kind="text",
        icon="✉",
        accent="#ffcf7b",
        params={"speed": 4, "rainbow": False, "text": "SEND GODDARD A MESSAGE"},
        tags=("agent", "message", "utility"),
        featured=True,
    ),
    CatalogApp(
        id="goddard_choice",
        title="Goddard's Choice",
        subtitle="Agent-selected premium still from the current moment.",
        category="Agent",
        kind="ai_image",
        icon="☉",
        accent="#9fd0ff",
        prompt="display a premium pixel-art scene that feels like an intelligent agent curated it for a productive creative workspace",
        tags=("agent", "still", "curated"),
        featured=True,
    ),
    CatalogApp(
        id="heartbeat_scene",
        title="Heartbeat Scene",
        subtitle="Use the current heartbeat summary as display guidance.",
        category="Agent",
        kind="ai_image",
        icon="♥",
        accent="#ff7f9e",
        prompt="display an elegant pixel-art scene inspired by the latest Goddard heartbeat",
        tags=("agent", "heartbeat", "context"),
        featured=True,
    ),
)


COLLECTIONS: tuple[CatalogCollection, ...] = (
    CatalogCollection(
        id="desk_cycle",
        title="Desk Cycle",
        subtitle="Useful first, beautiful second.",
        description="Clock, weather, ambient motion, and one premium art moment.",
        app_ids=("hero_clock", "weather_now", "signal_starfield", "aurora_pines", "koi_moon"),
        accent="#8fe0cf",
    ),
    CatalogCollection(
        id="after_dark",
        title="After Dark",
        subtitle="Night scenes with motion and contrast.",
        description="A moody evening rotation tuned for distance readability.",
        app_ids=("city_rain", "storm_lighthouse", "dragon_forge", "jellyfish_bloom", "warp_tunnel"),
        accent="#7ea3ff",
    ),
    CatalogCollection(
        id="retro_showcase",
        title="Retro Showcase",
        subtitle="Arcade cabinet energy.",
        description="Sprite-forward scenes and motion with a classic palette bias.",
        app_ids=("synth_sunset", "arcade_racer", "mario_stage", "metroid_core", "calm_rainbow"),
        accent="#ffb36b",
    ),
    CatalogCollection(
        id="agent_autopilot",
        title="Agent Autopilot",
        subtitle="Goddard drives the wall.",
        description="Message, weather, and AI scenes designed for automation hooks.",
        app_ids=("message_board", "weather_now", "goddard_choice", "heartbeat_scene", "hero_clock"),
        accent="#ff96b2",
    ),
)


_APP_INDEX = {app.id: app for app in APPS}
_COLLECTION_INDEX = {collection.id: collection for collection in COLLECTIONS}


def get_app(app_id: str) -> CatalogApp:
    try:
        return _APP_INDEX[app_id]
    except KeyError as exc:
        raise KeyError(f"unknown_app:{app_id}") from exc


def get_collection(collection_id: str) -> CatalogCollection:
    try:
        return _COLLECTION_INDEX[collection_id]
    except KeyError as exc:
        raise KeyError(f"unknown_collection:{collection_id}") from exc


def collection_app_ids(collection_id: str) -> list[str]:
    return list(get_collection(collection_id).app_ids)


def catalog_payload() -> dict[str, object]:
    return {
        "apps": [app.to_dict() for app in APPS],
        "collections": [collection.to_dict() for collection in COLLECTIONS],
    }
