# 📦 Guide d'installation

## 1. Prérequis matériel

- Onduleur **Axpert / WKS EVO** avec port RS232
- Convertisseur **USB/RS232** (Prolific PL2303 ou FTDI FT232 recommandés — éviter CH340)
- Câble RS232 vers port série de l'onduleur
- Home Assistant OS installé

## 2. Identifier le port série

Dans le terminal HA :

```bash
ls /dev/serial/by-id/
```

Utiliser le chemin `/dev/serial/by-id/` pour éviter les changements de port après redémarrage.

## 3. Tester la communication

```bash
stty -F /dev/ttyUSB0 2400 cs8 -cstopb -parenb raw
printf '\x51\x50\x49\x47\x53\xB7\xA9\x0D' > /dev/ttyUSB0 & cat /dev/ttyUSB0
```

Une réponse commençant par `(` confirme que la communication fonctionne.

## 4. Installer le custom component

```bash
mkdir -p /config/custom_components/axpert
```

Copier les fichiers `custom_components/axpert/` dans `/config/custom_components/axpert/`.

## 5. Configurer configuration.yaml

Ajouter le contenu de `config/configuration.yaml` à votre `/config/configuration.yaml`.

Adapter le chemin du port série :
```yaml
sensor:
  - platform: axpert
    port: /dev/serial/by-id/VOTRE_CONVERTISSEUR
    baud: 2400
```

## 6. Installer les automatisations

Créer `/config/automations/` et copier les fichiers YAML.

Dans `configuration.yaml`, remplacer :
```yaml
automation: !include automations.yaml
```
Par :
```yaml
automation: !include_dir_merge_list automations/
```

## 7. Ajouter les helpers

Ajouter dans `configuration.yaml` :
```yaml
input_boolean:
  onduleur_mode_manuel:
    name: "Onduleur Mode Manuel"
    icon: mdi:hand-back-right

input_datetime:
  onduleur_dernier_switch:
    name: "Onduleur Dernier Switch"
    has_date: true
    has_time: true

counter:
  onduleur_switchs_jour:
    name: "Onduleur Switchs Aujourd'hui"
    initial: 0
    step: 1
    icon: mdi:counter
```

## 8. Redémarrer Home Assistant

```bash
ha core restart
```

## 9. Vérifier les entités

Dans **Paramètres → Appareils et Services → Entités**, rechercher `axpert`.
