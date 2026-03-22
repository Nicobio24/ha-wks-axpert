# 🔋 Home Assistant — Intégration Onduleur WKS EVO / Axpert

Intégration complète d'un onduleur **WKS EVO Circle 5.6kW** (rebrand Axpert/Voltronic) dans Home Assistant OS, avec automatisations intelligentes de gestion de l'énergie solaire.

## 📋 Matériel testé

| Composant | Modèle |
|---|---|
| Onduleur | WKS EVO Circle 5.6kW (Axpert/Voltronic) |
| Batterie | Pylontech US3000 (48V / 3.5kWh) |
| Panneaux | 2.4 kWc |
| Convertisseur | USB/RS232 Prolific PL2303 |
| Serveur HA | PC x86_64 / Raspberry Pi 3B+ |

## ✨ Fonctionnalités

- 📊 **14 capteurs temps réel** — tension, courant, puissance, température...
- ☀️ **Puissance PV** calculée depuis l'index natif de l'onduleur
- 🔋 **SOC batterie** et capteur de mode (SUB/SBU)
- ⚡ **Tableau de bord Énergie** HA complet
- 🤖 **Automatisations intelligentes** SBU/SUB avec garde-fous
- 🌅 **Basé sur coucher du soleil** pour la sécurité nocturne
- 📱 **Notifications** sur téléphone à chaque changement de mode
- 🔄 **Watchdog** automatique en cas de gel du port série

## 🗂️ Structure du projet

```
ha-wks-axpert/
├── README.md
├── custom_components/
│   └── axpert/
│       ├── __init__.py
│       ├── manifest.json
│       └── sensor.py
├── automations/
│   ├── automations_onduleur.yaml
│   └── automations_watchdog.yaml
├── config/
│   └── configuration.yaml
└── docs/
    ├── installation.md
    ├── configuration.md
    └── troubleshooting.md
```

## 🚀 Installation rapide

Voir [docs/installation.md](docs/installation.md) pour le guide complet.

## 📡 Capteurs disponibles

| Entité | Description | Unité |
|---|---|---|
| `sensor.axpert_puissance_pv` | Puissance panneaux solaires | W |
| `sensor.axpert_soc_batterie` | État de charge batterie | % |
| `sensor.axpert_tension_batterie` | Tension batterie | V |
| `sensor.axpert_puissance_active` | Consommation maison | W |
| `sensor.axpert_mode` | Mode onduleur (SUB/SBU) | - |
| `sensor.axpert_temperature_onduleur` | Température onduleur | °C |
| `sensor.axpert_tension_pv` | Tension panneaux | V |
| `sensor.axpert_courant_pv` | Courant panneaux | A |
| `sensor.axpert_tension_ac_entree` | Tension réseau EDF | V |
| `sensor.axpert_tension_ac_sortie` | Tension sortie onduleur | V |
| `sensor.axpert_puissance_apparente` | Puissance apparente | VA |
| `sensor.axpert_frequence_entree` | Fréquence réseau | Hz |
| `sensor.axpert_courant_charge_batterie` | Courant charge batterie | A |
| `sensor.axpert_charge_sortie` | Charge sortie onduleur | % |

## 🤖 Automatisations

| Automatisation | Déclencheur | Action |
|---|---|---|
| Passage SBU | PV > 50W ET SOC > 50% | → Mode batterie |
| Passage SUB | Déficit PV > 50% conso ET SOC < 90% | → Mode réseau |
| Protection batterie | SOC < 20% | → SUB forcé + notif |
| Sécurité coucher soleil | 1h avant coucher | → SUB forcé |
| Anti-oscillation | > 6 switchs/jour | → Mode manuel |
| Watchdog | Pas de données > 5min | → Redémarre HA |

## 📜 Licence

MIT — Libre d'utilisation et de modification.

## 🤝 Contribution

Les PR sont les bienvenues ! Testé sur WKS EVO Circle 5.6kW.
Retours bienvenus pour d'autres modèles Axpert/Voltronic.
