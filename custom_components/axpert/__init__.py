import threading
import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "axpert"
PLATFORMS = ["sensor"]
SCAN_INTERVAL = timedelta(seconds=30)

QMOD_MAP = {
    'B': 'SBU - Battery mode',
    'L': 'SUB - Line mode',
    'P': 'Power on mode',
    'S': 'Standby mode',
    'F': 'Fault mode',
    'H': 'Power saving mode',
}


# ---------------------------------------------------------------------------
# Connexion via wks-com
# ---------------------------------------------------------------------------

class AxpertWKS:
    """
    Encapsule wks_com.inverter.Inverter avec polling thread + lock.
    Gère QPIGS (status), QMOD (mode), QED (énergie jour), QET (énergie totale).
    """

    def __init__(self, port):
        self._port = port
        self._inv = None
        self._lock = threading.Lock()
        self._running = False
        self._status = {}
        self._mode = None
        self._daily_pv = None
        self._total_pv = None
        self._poll_thread = None

    def start(self):
        self._running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            name="axpert_wks_poll",
            daemon=True
        )
        self._poll_thread.start()
        _LOGGER.info("AxpertWKS: démarré sur %s", self._port)

    def stop(self):
        self._running = False
        # Fermer le port série immédiatement pour libérer le verrou
        with self._lock:
            if self._inv is not None:
                try:
                    self._inv.close()
                except Exception:
                    pass
                self._inv = None
        # Attendre la fin du thread (max 5s)
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=5)
        _LOGGER.info("AxpertWKS: arrêté")

    def get_status(self):
        return self._status

    def get_mode(self):
        return self._mode

    def get_daily_pv(self):
        return self._daily_pv

    def get_total_pv(self):
        return self._total_pv

    def send_command(self, mode: str) -> bool:
        cmd = "POP01" if mode.upper() == "SUB" else "POP02"
        with self._lock:
            inv = self._get_inverter()
            if inv is None:
                return False
            try:
                inv.write(cmd)
                time.sleep(0.5)
                response = inv.read().decode("utf-8", errors="ignore")
                _LOGGER.debug("send_command %s → %s", cmd, repr(response))
                if "(ACK" in response:
                    _LOGGER.info("send_command: %s → ACK ✓", mode)
                    return True
                elif "(NAK" in response:
                    _LOGGER.warning("send_command: %s → NAK", mode)
                else:
                    _LOGGER.warning("send_command: %s → réponse inattendue: %s", mode, repr(response))
                return False
            except Exception as e:
                _LOGGER.error("send_command: erreur: %s", e)
                self._inv = None
                return False

    def query_mode_now(self):
        with self._lock:
            self._do_poll_mode()
        return self._mode

    def _get_inverter(self):
        if self._inv is None:
            try:
                from wks_com.inverter import Inverter
                self._inv = Inverter(self._port, timeout=3)
                _LOGGER.info("AxpertWKS: connexion ouverte sur %s", self._port)
            except Exception as e:
                _LOGGER.warning("AxpertWKS: impossible d'ouvrir %s: %s", self._port, e)
                self._inv = None
        return self._inv

    def _poll_loop(self):
        while self._running:
            with self._lock:
                self._do_poll_status()
            time.sleep(2)
            with self._lock:
                self._do_poll_mode()
            time.sleep(2)
            with self._lock:
                self._do_poll_energy()
            for _ in range(26):
                if not self._running:
                    break
                time.sleep(1)

    def _do_poll_status(self):
        inv = self._get_inverter()
        if inv is None:
            return
        try:
            result = inv.send("QPIGS")
            if isinstance(result, dict) and result:
                self._status = result
                _LOGGER.debug("QPIGS: %s", result)
            else:
                _LOGGER.warning("AxpertWKS: QPIGS réponse invalide: %s", repr(result))
                if result == "NAK":
                    self._inv = None
        except Exception as e:
            _LOGGER.warning("AxpertWKS: erreur QPIGS: %s", e)
            self._inv = None

    def _do_poll_mode(self):
        inv = self._get_inverter()
        if inv is None:
            return
        try:
            result = inv.send("QMOD")
            letter = None
            if isinstance(result, str):
                stripped = result.strip().upper()
                letter = stripped[0] if stripped else None
                if letter == "(":
                    letter = stripped[1] if len(stripped) > 1 else None
            elif isinstance(result, dict):
                raw = str(result.get("mode", result.get("operating_mode", ""))).strip().upper()
                letter = raw[0] if raw else None
            if letter and letter in QMOD_MAP:
                self._mode = letter
                _LOGGER.debug("QMOD: %s → %s", letter, QMOD_MAP[letter])
            else:
                _LOGGER.debug("QMOD: réponse brute: %s", repr(result))
        except Exception as e:
            _LOGGER.warning("AxpertWKS: erreur QMOD: %s", e)

    def _do_poll_energy(self):
        inv = self._get_inverter()
        if inv is None:
            return
        try:
            daily = inv.send("QED")
            if daily and daily != "NAK":
                self._daily_pv = daily
                _LOGGER.debug("QED: %s", daily)
        except Exception as e:
            _LOGGER.debug("AxpertWKS: erreur QED: %s", e)
        try:
            total = inv.send("QET")
            if total and total != "NAK":
                self._total_pv = total
                _LOGGER.debug("QET: %s", total)
        except Exception as e:
            _LOGGER.debug("AxpertWKS: erreur QET: %s", e)


# ---------------------------------------------------------------------------
# Setup config entry
# ---------------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port = entry.data["port"]

    wks = AxpertWKS(port)
    await hass.async_add_executor_job(wks.start)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="axpert",
        update_method=lambda: hass.async_add_executor_job(wks.get_status),
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "wks": wks,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_set_mode(call):
        mode = call.data.get("mode", "").upper()
        if mode not in ("SUB", "SBU"):
            _LOGGER.error("axpert.set_mode: mode invalide '%s'", mode)
            return
        success = await hass.async_add_executor_job(wks.send_command, mode)
        if success:
            await hass.async_add_executor_job(wks.query_mode_now)
            await coordinator.async_refresh()
        else:
            _LOGGER.warning("axpert.set_mode: commande %s échouée", mode)

    hass.services.async_register(DOMAIN, "set_mode", handle_set_mode)
    _LOGGER.info("Service axpert.set_mode enregistré")

    async def _on_stop(event):
        await hass.async_add_executor_job(wks.stop)

    hass.bus.async_listen_once("homeassistant_stop", _on_stop)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(data["wks"].stop)
        hass.services.async_remove(DOMAIN, "set_mode")
    return unload_ok
