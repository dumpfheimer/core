"""Support for VELUX scenes."""
import asyncio

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.exceptions import PlatformNotReady

from . import _LOGGER, DATA_VELUX


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up scenes for Velux platform."""

    if not hass.data[DATA_VELUX].setup_complete:
        try:
            task = hass.data[DATA_VELUX].notify_setup()
            await asyncio.wait_for(task, timeout=120)
            if not hass.data[DATA_VELUX].setup_complete:
                raise PlatformNotReady
        except asyncio.TimeoutError:
            raise PlatformNotReady

    entities = [VeluxScene(scene) for scene in hass.data[DATA_VELUX].pyvlx.scenes]
    async_add_entities(entities)


class VeluxScene(Scene):
    """Representation of a Velux scene."""

    def __init__(self, scene):
        """Init velux scene."""
        _LOGGER.info("Adding Velux scene: %s", scene)
        self.scene = scene

    @property
    def name(self):
        """Return the name of the scene."""
        return self.scene.name

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        await self.scene.run(wait_for_completion=False)
