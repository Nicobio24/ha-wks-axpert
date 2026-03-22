import serial
import logging
import time
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    UnitOfPower, UnitOfElectricPotential,
    UnitOfElectricCurrent, UnitOfTemperature,
    UnitOfFrequency, PERCENTAGE
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity, DataUpdateCoordinator
)

_LOGGER = logging.getLogger(__name__)
DOMAIN = "axpert"
SCAN_INTERVAL = timedelta(seconds=30)
QPIGS_CMD = b'\x51\x50\x49\x47\x53\xB7\xA9\x0D'

SENSORS = [
    ("grid_voltage",             "Tension AC entrée",        UnitOfElectricPotential.VOLT, "voltage",         0),
    ("grid_frequency",           "Fréquence entrée",         UnitOfFrequency.HERTZ,        "frequency",       1),
    ("ac_output_voltage",        "Tension AC sortie",        UnitOfElectricPotential.VOLT, "voltage",         2),
    ("ac_output_frequency",      "Fréquence sortie",         UnitOfFrequency.HERTZ,        "frequency",       3),
    ("ac_output_apparent_power", "Puissance apparente",      "VA",                         "apparent_power",  4),
    ("ac_output_active_power",   "Puissance active",         UnitOfPower.WATT,             "power",           5),
    ("output_load_percent",      "Charge sortie",            PERCENTAGE,                   None,              6),
    ("battery_voltage",          "Tension batterie",         UnitOfElectricPotential.VOLT, "voltage",         8),
    ("battery_charging_current", "Courant charge batterie",  UnitOfElectricCurrent.AMPERE, "current",         9),
    ("battery_capacity",         "SOC batterie",             PERCENTAGE,                   "battery",         10),
    ("inverter_temperature",     "Température onduleur",     UnitOfTemperature.CELSIUS,    "temperature",     11),
    ("pv_input_current",         "Courant PV",               UnitOfElectricCurrent.AMPERE, "current",         12),
    ("pv_input_voltage",         "Tension PV",               UnitOfElectricPotential.VOLT, "voltage",         13),
]

def read_qpigs(port, baud=2400, retries=3):
    ser = None
    for attempt in range(retries):
        try:
            ser = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=3,
                write_timeout=3
            )
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.write(QPIGS_CMD)
            ser.flush()
            time.sleep(0.5)
            response = ser.read(200).decode("utf-8", errors="ignore")

            if response.startswith("(") and len(response) > 50:
                fields = response[1:].split()
                # Logger les flags pour debug
                if len(fields) > 16:
                    _LOGGER.warning("AXPERT DEBUG - Tous les champs: %s", fields)
                    _LOGGER.warning("AXPERT DEBUG - Index 16 (flags): %s", fields[16])
                    _LOGGER.warning("AXPERT DEBUG - Index 17: %s", fields[17] if len(fields) > 17 else "N/A")
                    _LOGGER.warning("AXPERT DEBUG - Index 18: %s", fields[18] if len(fields) > 18 else "N/A")
                return fields
            else:
                _LOGGER.warning("Réponse invalide (tentative %d): %s", attempt+1, repr(response))

        except serial.SerialTimeoutException:
            _LOGGER.warning("Timeout port série (tentative %d/%d)", attempt+1, retries)
        except serial.SerialException as e:
            _LOGGER.warning("Erreur série (tentative %d/%d): %s", attempt+1, retries, e)
        except Exception as e:
            _LOGGER.error("Erreur inattendue (tentative %d/%d): %s", attempt+1, retries, e)
        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass
            ser = None
        if attempt < retries - 1:
            time.sleep(2)

    return None

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    port = config.get("port", "/dev/ttyUSB0")
    baud = config.get("baud", 2400)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="axpert",
        update_method=lambda: hass.async_add_executor_job(read_qpigs, port, baud),
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_refresh()

    entities = []
    for sensor_id, name, unit, device_class, index in SENSORS:
        entities.append(AxpertSensor(coordinator, sensor_id, name, unit, device_class, index))

    entities.append(AxpertPVPower(coordinator))
    entities.append(AxpertMode(coordinator))
    async_add_entities(entities)

class AxpertSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, sensor_id, name, unit, device_class, index):
        super().__init__(coordinator)
        self._attr_name = f"Axpert {name}"
        self._attr_unique_id = f"axpert_{sensor_id}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._index = index

    @property
    def native_value(self):
        data = self.coordinator.data
        if data and self._index < len(data):
            try:
                return float(data[self._index])
            except ValueError:
                return None
        return None

class AxpertPVPower(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Axpert Puissance PV"
        self._attr_unique_id = "axpert_pv_input_power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = "power"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        data = self.coordinator.data
        if data and len(data) > 19:
            try:
                return float(data[19])
            except ValueError:
                return None
        return None

class AxpertMode(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Axpert Mode"
        self._attr_unique_id = "axpert_inverter_mode"
        self._attr_icon = "mdi:solar-power"

    @property
    def native_value(self):
        data = self.coordinator.data
        if data and len(data) > 16:
            try:
                flags = data[16]
                _LOGGER.warning("AXPERT MODE - flags bruts: %s", flags)
                if len(flags) >= 8:
                    bit1 = int(flags[-2])
                    return "SBU - Battery mode" if bit1 == 1 else "SUB - Line mode"
            except Exception as e:
                _LOGGER.error("Erreur décodage mode: %s", e)
                return None
        return None
