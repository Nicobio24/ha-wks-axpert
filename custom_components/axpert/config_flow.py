import voluptuous as vol
from homeassistant import config_entries
from . import DOMAIN


class AxpertConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Évite les doublons
            await self.async_set_unique_id(user_input["port"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Axpert ({user_input['port']})",
                data=user_input,
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("port", default="/dev/ttyUSB0"): str,
            }),
            errors=errors,
        )
