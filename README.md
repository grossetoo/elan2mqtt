# eLAN MQTT Gateway - Home Assistant Add-on

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

## 🎯 O add-onu

Tento add-on propojuje **Elko EP eLAN** systém s **Home Assistantem** přes **MQTT**.

### ✨ Hlavní vlastnosti:

- ✅ **Automatické objevování zařízení** (MQTT Discovery)
- ✅ **Climate entity** s plnou podporou termostatů (HeatCoolArea + RFATV-1)
- ✅ **Preset módy** (Away, Eco, Comfort, Boost)
- ✅ **Ovládání světel** (RFDA-11B dimery, RFSA spínače)
- ✅ **Detektory** (okna, dveře, kouř, pohyb, zaplavení)
- ✅ **Teploměry** (RFTI-10B)

---

## 📋 Instalace

### 1. Přidej repository do Home Assistantu

Settings → Add-ons → Add-on Store → ⋮ (vpravo nahoře) → Repositories

Přidej URL:
```
https://github.com/grossetoo/elan2mqtt
```

**Poznámka:** Nahraď `YOUR_USERNAME` svým GitHub uživatelským jménem.

### 2. Instaluj add-on

V Add-on Store najdi **"eLAN MQTT Gateway"** a klikni na **Install**.

### 3. Konfigurace

V záložce **Configuration** nastav své hodnoty:

```yaml
eLanURL: "http://YOUR_ELAN_IP"
MQTTserver: "mqtt://mqtt_user:mqtt_password@core-mosquitto"
username: "admin"
password: "your_elan_password"
log_level: "info"
disable_autodiscovery: false
mqtt_id: ""
```

**Parametry:**
- `eLanURL` - IP adresa tvého eLAN zařízení
- `MQTTserver` - MQTT broker (obvykle `mqtt://user:password@core-mosquitto`)
- `username` - uživatelské jméno pro eLAN
- `password` - heslo pro eLAN
- `log_level` - úroveň logování (debug, info, warning, error, fatal)
- `disable_autodiscovery` - vypnout automatické objevování (true/false)
- `mqtt_id` - volitelné MQTT Client ID

### 4. Start

Klikni na **Start** a zkontroluj **Log**.

---

## 🏠 Podporovaná zařízení

### Climate (termostaty)
- **HeatCoolArea** management + **RFATV-1** hlavice
- Automaticky vytváří:
  - Climate entity (preset módy)
  - Number entity (korekce teploty -5 až +5°C)
  - Select entity (režim: Outside/Cold/Comfort/Warm)
  - Switch entity (zapnuto/vypnuto)
  - Binary senzory (okno, baterie, zamčeno, chyba)
  - Sensor (ventil %)

### Světla
- **RFDA-11B** - dimer
- Ostatní light entity

### Spínače
- **RFSA-61M, RFSA-66M, RFSA-11B, RFSA-62B, RFUS-61**

### Detektory
- **RFWD-100** - okna/dveře
- **RFSD** - kouř
- **RFMD** - pohyb
- **RFSF-1B** - zaplavení

### Teploměry
- **RFTI-10B** - IN/OUT teplota

---

## 🔧 Konfigurace

| Parametr | Popis | Výchozí hodnota |
|----------|-------|-----------------|
| `eLanURL` | URL eLAN zařízení | `""` |
| `MQTTserver` | MQTT broker | `mqtt://user:password@core-mosquitto` |
| `username` | eLAN uživatel | `admin` |
| `password` | eLAN heslo | `elkoep` |
| `log_level` | Úroveň logování | `info` |
| `disable_autodiscovery` | Vypnout autodiscovery | `false` |
| `mqtt_id` | MQTT Client ID | `""` |

---

## 🐛 Podpora

Máš problém? Otevři issue na [GitHubu](https://github.com/grossetoo/elan2mqtt/issues).

---

## 📄 Licence

MIT License

---

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
