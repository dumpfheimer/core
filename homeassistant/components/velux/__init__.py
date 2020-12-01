"""Support for VELUX KLF 200 devices."""
import asyncio
import logging


from pyvlx import PyVLX, PyVLXException
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PASSWORD, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv

DOMAIN = "velux"
DATA_VELUX = "data_velux"
SUPPORTED_DOMAINS = ["cover", "scene"]
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {vol.Required(CONF_HOST): cv.string, vol.Required(CONF_PASSWORD): cv.string}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the velux component."""

    try:
        hass.data[DATA_VELUX] = VeluxModule(hass, config)
        hass.data[DATA_VELUX].setup()
        await hass.data[DATA_VELUX].load_components()
    except Exception as ex:
        _LOGGER.exception("Could not setup velux platform: %s", ex)

    return True


class VeluxModule:
    """Abstraction for velux component."""

    def __init__(self, hass, config):
        """Initialize for velux component."""
        self.pyvlx = None
        self._hass = hass
        self._domain_config = config[DOMAIN]
        self._config = config
        self.shutdown = False
        self.setup_complete = False
        self.starting = False
        self.start_task = None

    def setup(self):
        """Velux component setup."""

        async def on_hass_stop(event):
            """Close connection when hass stops."""

            _LOGGER.debug("Velux interface terminated")
            self.shutdown = True
            if self.start_task is not None:
                try:
                    self.start_task.cancel()
                except Exception as e:
                    _LOGGER.debug("Velux component start_task could not be cancelled %s", self.start_task)
            await self.pyvlx.disconnect()

        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_hass_stop)
        host = self._domain_config.get(CONF_HOST)
        password = self._domain_config.get(CONF_PASSWORD)
        self.pyvlx = PyVLX(host=host, password=password)

    async def load_components(self):
        """Trigger platform loading over hass."""

        _LOGGER.debug("Velux loading components")
        for component in SUPPORTED_DOMAINS:
            self._hass.async_create_task(
                discovery.async_load_platform(self._hass, component, DOMAIN, {}, self._config)
            )

    async def async_start(self):
        """Try to connect to KLF-200."""

        try:
            await self.pyvlx.load_scenes()
            await self.pyvlx.load_nodes()
            self.setup_complete = True
            _LOGGER.info("Velux component successfully connected to KLF-200")
        except Exception as ex:
            _LOGGER.info("Velux component could not connect to KLF-200: %s", ex)

        self.starting = False

    def notify_setup(self):
        """Notifies the component that a connection to KLF-200 is needed / to set up."""

        if self.shutdown:
            raise Exception("Setup of velux component requested after shutdown notified")

        if not self.starting:
            self.starting = True
            self.start_task = asyncio.create_task(self.async_start())

        return self.start_task
