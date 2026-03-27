import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import (
    UnitOfPower, UnitOfElectricPotential,
    UnitOfElectricCurrent, UnitOfTemperature,
    UnitOfFrequency, UnitOfEnergy, PERCENTAGE
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, QMOD_MAP

_LOGGER = logging.getLogger(__name__)

# (unique_id, nom, unité, device_class, clé wks-com, state_class)
SENSORS = [
    ("grid_voltage",             "Tension AC entrée",        UnitOfElectricPotential.VOLT,  "voltage",        "ac_input_voltage",                SensorStateClass.MEASUREMENT),
    ("grid_frequency",           "Fréquence entrée",         UnitOfFrequency.HERTZ,         "frequency",      "ac_input_frequency",              SensorStateClass.MEASUREMENT),
    ("ac_output_voltage",        "Tension AC sortie",        UnitOfElectricPotential.VOLT,  "voltage",        "ac_output_voltage",               SensorStateClass.MEASUREMENT),
    ("ac_output_frequency",      "Fréquence sortie",         UnitOfFrequency.HERTZ,         "frequency",      "ac_output_frequency",             SensorStateClass.MEASUREMENT),
    ("ac_output_apparent_power", "Puissance apparente",      "VA",                          "apparent_power", "ac_output_apparent_power",        SensorStateClass.MEASUREMENT),
    ("ac_output_active_power",   "Puissance active",         UnitOfPower.WATT,              "power",          "ac_output_active_power",          SensorStateClass.MEASUREMENT),
    ("output_load_percent",      "Charge sortie",            PERCENTAGE,                    None,             "ac_load_percentage",              SensorStateClass.MEASUREMENT),
    ("battery_voltage",          "Tension batterie",         UnitOfElectricPotential.VOLT,  "voltage",        "battery_voltage",                 SensorStateClass.MEASUREMENT),
    ("battery_charging_current", "Courant charge batterie",  UnitOfElectricCurrent.AMPERE,  "current",        "battery_charging_current",        SensorStateClass.MEASUREMENT),
    ("battery_capacity",         "SOC batterie",             PERCENTAGE,                    "battery",        "battery_capacity",                SensorStateClass.MEASUREMENT),
    ("inverter_temperature",     "Température onduleur",     UnitOfTemperature.CELSIUS,     "temperature",    "inverter_heat_sink_temperature",  SensorStateClass.MEASUREMENT),
    ("pv_input_current",         "Courant PV",               UnitOfElectricCurrent.AMPERE,  "current",        "pv1_input_current",               SensorStateClass.MEASUREMENT),
    ("pv_input_voltage",         "Tension PV",               UnitOfElectricPotential.VOLT,  "voltage",        "pv1_input_voltage",               SensorStateClass.MEASUREMENT),
    ("battery_discharge_current","Courant décharge batterie",UnitOfElectricCurrent.AMPERE,  "current",        "battery_discharge_current",       SensorStateClass.MEASUREMENT),
]


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    wks = data["wks"]

    entities = []
    for sensor_id, name, unit, device_class, wks_key, state_class in SENSORS:
        entities.append(AxpertSensor(coordinator, sensor_id, name, unit, device_class, wks_key, state_class))
    entities.append(AxpertPVPower(coordinator))
    entities.append(AxpertMode(coordinator, wks))
    entities.append(AxpertDailyPVEnergy(coordinator, wks))
    entities.append(AxpertTotalPVEnergy(coordinator, wks))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Entités
# ---------------------------------------------------------------------------

class AxpertSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, sensor_id, name, unit, device_class, wks_key, state_class):
        super().__init__(coordinator)
        self._attr_name = f"Axpert {name}"
        self._attr_unique_id = f"axpert_{sensor_id}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._wks_key = wks_key

    @property
    def native_value(self):
        data = self.coordinator.data
        if not isinstance(data, dict):
            return None
        val = data.get(self._wks_key)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None


class AxpertPVPower(CoordinatorEntity, SensorEntity):
    """Puissance PV = tension × courant (champ calculé)."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Axpert Puissance PV"
        self._attr_unique_id = "axpert_pv_input_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = "power"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        data = self.coordinator.data
        if not isinstance(data, dict):
            return None
        try:
            v = float(data.get("pv1_input_voltage", 0))
            i = float(data.get("pv1_input_current", 0))
            return round(v * i, 1)
        except (ValueError, TypeError):
            return None


class AxpertMode(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, wks):
        super().__init__(coordinator)
        self._wks = wks
        self._attr_name = "Axpert Mode"
        self._attr_unique_id = "axpert_inverter_mode"
        self._attr_icon = "mdi:solar-power"

    @property
    def native_value(self):
        letter = self._wks.get_mode()
        if letter is not None:
            return QMOD_MAP.get(letter)
        return None


def _extract_kwh(data) -> float | None:
    if data is None:
        return None
    if isinstance(data, (int, float)):
        return round(float(data) / 1000, 3)
    if isinstance(data, dict):
        for key in (
            "pv_generated_energy_for_day",
            "pv_generated_energy_total",
            "pv_energy", "energy", "kwh",
        ):
            if key in data:
                try:
                    return round(float(data[key]) / 1000, 3)
                except (ValueError, TypeError):
                    pass
        for val in data.values():
            try:
                return round(float(val) / 1000, 3)
            except (ValueError, TypeError):
                continue
    return None


class AxpertDailyPVEnergy(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, wks):
        super().__init__(coordinator)
        self._wks = wks
        self._attr_name = "Axpert Énergie PV jour"
        self._attr_unique_id = "axpert_daily_pv_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = "energy"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:solar-panel"

    @property
    def native_value(self):
        return _extract_kwh(self._wks.get_daily_pv())


class AxpertTotalPVEnergy(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, wks):
        super().__init__(coordinator)
        self._wks = wks
        self._attr_name = "Axpert Énergie PV totale"
        self._attr_unique_id = "axpert_total_pv_energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = "energy"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:solar-panel-large"

    @property
    def native_value(self):
        return _extract_kwh(self._wks.get_total_pv())
