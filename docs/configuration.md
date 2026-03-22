# ⚙️ Guide de configuration

## Paramètres ajustables

### Seuils des automatisations

Dans `automations/automations_onduleur.yaml` :

| Paramètre | Valeur défaut | Description |
|---|---|---|
| PV seuil SBU | 50W | Puissance PV minimale pour passer en SBU |
| SOC minimum SBU | 50% | SOC minimum pour passer en SBU |
| Déficit SUB | 50% | Déficit PV/conso pour passer en SUB |
| SOC maximum SUB | 90% | SOC max avant de rester en SBU |
| Délai entre switchs | 10 min | Délai minimum entre deux changements de mode |
| Max switchs/jour | 6 | Nombre maximum de switchs par jour |
| Délai mode manuel | 30 min | Durée du mode manuel avant retour auto |
| Sécurité coucher | 1h avant | Bascule SUB avant le coucher du soleil |

### Commandes série

| Mode | Commande |
|---|---|
| SUB — Solar Utility Battery (Grid first) | POP01 |
| SBU — Solar Battery Utility (Battery first) | POP02 |

⚠️ Les codes POP peuvent varier selon le firmware. Tester manuellement avant d'activer les automatisations.
