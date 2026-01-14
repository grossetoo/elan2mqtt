# -*- coding: utf-8 -*-

##########################################################################
#
# This is eLAN to MQTT gateway - VERSION WITH CLIMATE AUTODISCOVERY
#
# Modified to support full climate entity discovery for HeatCoolArea + RFATV-1
#
##########################################################################

import argparse
import aiohttp
import asyncio
import async_timeout

import paho.mqtt.client as mqtt

import json

import logging
import time

import hashlib

logger = logging.getLogger(__name__)



async def main():
    # placehloder for devices data
    d = {}
    # placeholder for message que
    pending_message = []
    async def publish_status(mac):
        """Publish message to status topic. Topic syntax is: elan / mac / status """
        if mac in d:
            logger.info("Getting and publishing status for " + d[mac]['url'])
            resp = await session.get(d[mac]['url'] + '/state', timeout=3)
            logger.debug(resp.status)
            if resp.status != 200:
                # There was problem getting status of device from eLan
                # This is usually caused by expiration of login
                # Let's try to relogin
                logger.warning("Getting status of device from eLan failed. Trying to relogin and get status.")
                await login(args.elan_user[0], str(args.elan_password[0]).encode('cp1250'))
                resp = await session.get(d[mac]['url'] + '/state', timeout=3)
            assert resp.status == 200, "Status retreival from eLan failed!"
            state = await resp.json()
            mqtt_cli.publish(d[mac]['status_topic'],
                            bytearray(json.dumps(state), 'utf-8'))
            logger.info(
                "Status published for " + d[mac]['url'] + " " + str(state))

    async def publish_discovery(mac):
        """Publish message to status topic. Topic syntax is: elan / mac / status """
        if mac in d:
            if ("product type" in d[mac]['info']['device info']):
                # placeholder for device type versus protuct type check
                pass
            else:
                d[mac]['info']['device info']['product type'] = '---'
            logger.info("Publishing discovery for " + d[mac]['url'])

            # 1 User should set type to light. But sometimes...
            # That is why we will always treat RFDA-11B as a light dimmer
            #
            if ('light' in d[mac]['info']['device info']['type']) or ('lamp' in d[mac]['info']['device info']['type']) or (d[mac]['info']['device info']['product type'] == 'RFDA-11B'):
                logger.info(d[mac]['info']['device info'])

                if ('on' in d[mac]['info']['primary actions']):
                    logger.info("Primary action of light is ON")
                    discovery = {
                        'schema': 'basic',
                        'name': d[mac]['info']['device info']['label'],
                        'unique_id': ('eLan-' + mac),
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers' : ('eLan-light-' + mac),
                            'connections': [["mac",  mac]],
                            'mf': 'Elko EP',
                            'mdl': d[mac]['info']['device info']['product type']
                        },
                        'command_topic': d[mac]['control_topic'],
                        'state_topic': d[mac]['status_topic'],
                        'json_attributes_topic': d[mac]['status_topic'],
                        'payload_off': '{"on":false}',
                        'payload_on': '{"on":true}',
                        'state_value_template':
                        '{%- if value_json.on -%}{"on":true}{%- else -%}{"on":false}{%- endif -%}'
                    }
                    mqtt_cli.publish('homeassistant/light/' + mac + '/config',
                                    bytearray(json.dumps(discovery), 'utf-8'))
                    logger.info("Discovery 1.1. published for " + d[mac]['url'])
                    logger.debug(json.dumps(discovery))

                if ('brightness' in d[mac]['info']['primary actions']) or (d[mac]['info']['device info']['product type'] == 'RFDA-11B'):
                    logger.info("Primary action of light is BRIGHTNESS")
                    discovery = {
                        'schema': 'template',
                        'name': d[mac]['info']['device info']['label'],
                        'unique_id': ('eLan-' + mac),
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers' : ('eLan-dimmer-' + mac),
                            'connections': [["mac",  mac]],
                            'mf': 'Elko EP',
                            'mdl': d[mac]['info']['device info']['product type']
                        },
                        'state_topic': d[mac]['status_topic'],
                        #'json_attributes_topic': d[mac]['status_topic'],
                        'command_topic': d[mac]['control_topic'],
                        'command_on_template':
                        '{%- if brightness is defined -%} {"brightness": {{ (brightness * '
                        + str(d[mac]['info']['actions info']['brightness']
                              ['max']) +
                        ' / 255 ) | int }} } {%- else -%} {"brightness": 100 } {%- endif -%}',
                        'command_off_template': '{"brightness": 0 }',
                        'state_template':
                        '{%- if value_json.brightness > 0 -%}on{%- else -%}off{%- endif -%}',
                        'brightness_template':
                        '{{ (value_json.brightness * 255 / ' + str(
                            d[mac]['info']['actions info']['brightness']
                            ['max']) + ') | int }}'
                    }
                    mqtt_cli.publish('homeassistant/light/' + mac + '/config',
                                    bytearray(json.dumps(discovery), 'utf-8'))
                    logger.info("Discovery 1.2. published for " + d[mac]['url'])
                    logger.debug(json.dumps(discovery))

            #
            # 2. Switches
            # RFSA-6xM units and "appliance" class of eLan
            # Note: handled as ELSE of light entities to avoid lights on RFSA-6xM units
            elif ('appliance' in d[mac]['info']['device info']['type']) or (d[mac]['info']['device info']['product type'] == 'RFSA-61M') or (d[mac]['info']['device info']['product type'] == 'RFSA-66M') or (d[mac]['info']['device info']['product type'] == 'RFSA-11B')  or (d[mac]['info']['device info']['product type'] == 'RFUS-61') or (d[mac]['info']['device info']['product type'] == 'RFSA-62B'):
                logger.info(d[mac]['info']['device info'])
                # "on" primary action is required for switches
                if ('on' in d[mac]['info']['primary actions']):
                    logger.info("Primary action of device is ON")
                    discovery = {
                        'schema': 'basic',
                        'name': d[mac]['info']['device info']['label'],
                        'unique_id': ('eLan-' + mac),
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers': ('eLan-switch-' + mac),
                            'connections': [["mac",  mac]],
                            'mf': 'Elko EP',
                            'mdl': d[mac]['info']['device info']['product type']
                        },
                        'command_topic': d[mac]['control_topic'],
                        'state_topic': d[mac]['status_topic'],
                        'json_attributes_topic': d[mac]['status_topic'],
                        'payload_off': '{"on":false}',
                        'payload_on': '{"on":true}',
                        'state_off': 'off',
                        'state_on' : 'on',
                        'value_template':
                        '{%- if value_json.on -%}on{%- else -%}off{%- endif -%}'
                    }
                    mqtt_cli.publish('homeassistant/switch/' + mac + '/config',
                                    bytearray(json.dumps(discovery), 'utf-8'))
                    logger.info("Discovery 2. published for " + d[mac]['url'])
                    logger.debug(json.dumps(discovery))


            #
            # 3. Thermostats - CLIMATE AUTODISCOVERY (MODIFIED)
            #
            if (d[mac]['info']['device info']['type'] == 'temperature regulation area'):
                # HeatCoolArea management - pouze řídící funkce
                logger.info("Publishing climate discovery for HeatCoolArea: " + str(d[mac]['info']['device info']))

                # Najdi MAC adresu propojené RFATV-1 hlavice
                thermostat_mac = None
                if 'temperature sensor' in d[mac]['info']:
                    # temperature sensor obsahuje: {'57844': 'temperature'}
                    for sensor_id in d[mac]['info']['temperature sensor']:
                        thermostat_mac = sensor_id
                        break

                if thermostat_mac is None:
                    logger.warning(f"HeatCoolArea {mac} nemá propojenou RFATV-1 hlavici!")
                else:
                    # Climate entity - hlavní termostat
                    climate_discovery = {
                        'unique_id': f'eLan-climate-{mac}',
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers': [f'eLan-climate-{mac}'],
                            'connections': [["device_id", mac]],
                            'manufacturer': 'Elko EP',
                            'model': 'HeatCoolArea'
                        },
                        # Aktuální teplota z RFATV-1 hlavice
                        'current_temperature_topic': f'eLan/{thermostat_mac}/status',
                        'current_temperature_template': '{{ value_json.temperature }}',

                        # Požadovaná teplota z managementu
                        'temperature_state_topic': f'eLan/{mac}/status',
                        'temperature_state_template': "{{ value_json['requested temperature'] }}",

                        # Mode (heat/off)
                        'mode_state_topic': f'eLan/{mac}/status',
                        'mode_state_template': '{% if value_json.power == 0 %}off{% else %}heat{% endif %}',
                        'mode_command_topic': f'eLan/{mac}/command',
                        'mode_command_template': '{% if value == "off" %}{"power": 0}{% elif value == "heat" %}{"power": 1, "mode": 3}{% endif %}',
                        'modes': ['off', 'heat'],

                        # Preset módy (away/eco/comfort/boost)
                        'preset_mode_command_topic': f'eLan/{mac}/command',
                        'preset_mode_command_template': '{% if value == "away" %}{"mode": 1}{% elif value == "eco" %}{"mode": 2}{% elif value == "comfort" %}{"mode": 3}{% elif value == "boost" %}{"mode": 4}{% endif %}',
                        'preset_modes': ['away', 'eco', 'comfort', 'boost'],

                        # Rozsah teploty
                        'min_temp': 5,
                        'max_temp': 29,
                        'temp_step': 0.5,
                        'temperature_unit': 'C',
                        'precision': 0.5,

                        # JSON atributy z managementu
                        'json_attributes_topic': f'eLan/{mac}/status'
                    }

                    mqtt_cli.publish(f'homeassistant/climate/{mac}/config',
                                    bytearray(json.dumps(climate_discovery), 'utf-8'))
                    logger.info(f"Climate discovery published for {d[mac]['url']}")
                    logger.debug(json.dumps(climate_discovery))

                    # Number entity - Temperature Correction
                    number_correction = {
                        'name': 'Correction',
                        'unique_id': f'eLan-{mac}-correction',
                        'device': {
                            'identifiers': [f'eLan-climate-{mac}']
                        },
                        'command_topic': f'eLan/{mac}/command',
                        'command_template': '{"correction": {{ value }} }',
                        'state_topic': f'eLan/{mac}/status',
                        'value_template': '{{ value_json.correction }}',
                        'min': -5,
                        'max': 5,
                        'step': 0.5,
                        'unit_of_measurement': '°C',
                        'icon': 'mdi:thermometer-plus'
                    }
                    mqtt_cli.publish(f'homeassistant/number/{mac}/correction/config',
                                    bytearray(json.dumps(number_correction), 'utf-8'))

                    # Select entity - Mode
                    select_mode = {
                        'name': 'Mode',
                        'unique_id': f'eLan-{mac}-mode',
                        'device': {
                            'identifiers': [f'eLan-climate-{mac}']
                        },
                        'command_topic': f'eLan/{mac}/command',
                        'command_template': '{% if value == "Outside" %}{"mode": 1}{% elif value == "Cold" %}{"mode": 2}{% elif value == "Comfort" %}{"mode": 3}{% elif value == "Warm" %}{"mode": 4}{% endif %}',
                        'state_topic': f'eLan/{mac}/status',
                        'value_template': '{% if value_json.mode == 1 %}Outside{% elif value_json.mode == 2 %}Cold{% elif value_json.mode == 3 %}Comfort{% elif value_json.mode == 4 %}Warm{% endif %}',
                        'options': ['Outside', 'Cold', 'Comfort', 'Warm'],
                        'icon': 'mdi:home-thermometer-outline'
                    }
                    mqtt_cli.publish(f'homeassistant/select/{mac}/mode/config',
                                    bytearray(json.dumps(select_mode), 'utf-8'))

                    # Switch entity - Power
                    switch_power = {
                        'name': 'Power',
                        'unique_id': f'eLan-{mac}-power',
                        'device': {
                            'identifiers': [f'eLan-climate-{mac}']
                        },
                        'command_topic': f'eLan/{mac}/command',
                        'payload_on': '{"power": 1}',
                        'payload_off': '{"power": 0}',
                        'state_topic': f'eLan/{mac}/status',
                        'value_template': '{% if value_json.power == 1 %}ON{% else %}OFF{% endif %}',
                        'icon': 'mdi:power'
                    }
                    mqtt_cli.publish(f'homeassistant/switch/{mac}/power/config',
                                    bytearray(json.dumps(switch_power), 'utf-8'))

                    logger.info(f"Climate entities published for HeatCoolArea {mac}")

            elif (d[mac]['info']['device info']['product type'] == 'RFATV-1'):
                # RFATV-1 hlavice - vytvoř kompletní senzorové zařízení
                logger.info("Publishing sensor device for RFATV-1: " + str(d[mac]['info']['device info']))

                device_label = d[mac]['info']['device info']['label']

                # Temperature sensor (hlavní entita)
                temp_sensor = {
                    'name': 'Temperature',
                    'unique_id': f'eLan-{mac}-temperature',
                    'device': {
                        'name': device_label,
                        'identifiers': [f'eLan-rfatv-{mac}'],
                        'connections': [["mac", mac]],
                        'manufacturer': 'Elko EP',
                        'model': 'RFATV-1'
                    },
                    'device_class': 'temperature',
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': '{{ value_json.temperature }}',
                    'unit_of_measurement': '°C'
                }
                mqtt_cli.publish(f'homeassistant/sensor/{mac}/temperature/config',
                                bytearray(json.dumps(temp_sensor), 'utf-8'))

                # Number entity - Window Sensitivity
                number_window_sens = {
                    'name': 'Window Sensitivity',
                    'unique_id': f'eLan-{mac}-window-sens',
                    'device': {
                        'identifiers': [f'eLan-rfatv-{mac}']
                    },
                    'command_topic': f'eLan/{mac}/command',
                    'command_template': '{"open window sensitivity": {{ value | int }} }',
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': "{{ value_json['open window sensitivity'] }}",
                    'min': 0,
                    'max': 3,
                    'step': 1,
                    'icon': 'mdi:window-open-variant'
                }
                mqtt_cli.publish(f'homeassistant/number/{mac}/window_sens/config',
                                bytearray(json.dumps(number_window_sens), 'utf-8'))

                # Number entity - Window Off Time
                number_window_time = {
                    'name': 'Window Off Time',
                    'unique_id': f'eLan-{mac}-window-time',
                    'device': {
                        'identifiers': [f'eLan-rfatv-{mac}']
                    },
                    'command_topic': f'eLan/{mac}/command',
                    'command_template': '{"open window off time": {{ value | int }} }',
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': "{{ value_json['open window off time'] }}",
                    'min': 0,
                    'max': 60,
                    'step': 10,
                    'unit_of_measurement': 'min',
                    'icon': 'mdi:timer'
                }
                mqtt_cli.publish(f'homeassistant/number/{mac}/window_time/config',
                                bytearray(json.dumps(number_window_time), 'utf-8'))

                # Binary sensor - Open Window
                binary_window = {
                    'name': 'Open Window',
                    'unique_id': f'eLan-{mac}-window',
                    'device': {
                        'identifiers': [f'eLan-rfatv-{mac}']
                    },
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': '{{ value_json["open window"] }}',
                    'device_class': 'window',
                    'payload_on': 'true',
                    'payload_off': 'false'
                }
                mqtt_cli.publish(f'homeassistant/binary_sensor/{mac}/window/config',
                                bytearray(json.dumps(binary_window), 'utf-8'))

                # Binary sensor - Battery (invertováno pro správný device_class)
                binary_battery = {
                    'name': 'Battery',
                    'unique_id': f'eLan-{mac}-battery',
                    'device': {
                        'identifiers': [f'eLan-rfatv-{mac}']
                    },
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': '{% if value_json.battery == true %}OFF{% else %}ON{% endif %}',
                    'device_class': 'battery',
                    'payload_on': 'ON',
                    'payload_off': 'OFF'
                }
                mqtt_cli.publish(f'homeassistant/binary_sensor/{mac}/battery/config',
                                bytearray(json.dumps(binary_battery), 'utf-8'))

                # Binary sensor - Locked
                binary_locked = {
                    'name': 'Locked',
                    'unique_id': f'eLan-{mac}-locked',
                    'device': {
                        'identifiers': [f'eLan-rfatv-{mac}']
                    },
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': '{{ value_json.locked }}',
                    'device_class': 'lock',
                    'payload_on': 'true',
                    'payload_off': 'false'
                }
                mqtt_cli.publish(f'homeassistant/binary_sensor/{mac}/locked/config',
                                bytearray(json.dumps(binary_locked), 'utf-8'))

                # Binary sensor - Error
                binary_error = {
                    'name': 'Error',
                    'unique_id': f'eLan-{mac}-error',
                    'device': {
                        'identifiers': [f'eLan-rfatv-{mac}']
                    },
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': '{{ value_json.error }}',
                    'device_class': 'problem',
                    'payload_on': 'true',
                    'payload_off': 'false'
                }
                mqtt_cli.publish(f'homeassistant/binary_sensor/{mac}/error/config',
                                bytearray(json.dumps(binary_error), 'utf-8'))

                # Sensor - Valve position
                sensor_valve = {
                    'name': 'Valve',
                    'unique_id': f'eLan-{mac}-valve',
                    'device': {
                        'identifiers': [f'eLan-rfatv-{mac}']
                    },
                    'state_topic': f'eLan/{mac}/status',
                    'value_template': "{{ value_json['open valve'] }}",
                    'unit_of_measurement': '%',
                    'icon': 'mdi:valve',
                    'device_class': 'power_factor'
                }
                mqtt_cli.publish(f'homeassistant/sensor/{mac}/valve/config',
                                bytearray(json.dumps(sensor_valve), 'utf-8'))

                logger.info(f"All sensor entities published for RFATV-1 {mac}")


            #
            # 4. Thermometers
            #
            if (d[mac]['info']['device info']['type'] == 'thermometer') or (d[mac]['info']['device info']['product type'] == 'RFTI-10B'):
                logger.info(d[mac]['info']['device info'])

                discovery = {
                    'name': d[mac]['info']['device info']['label'] + '-IN',
                    'unique_id': ('eLan-' + mac + '-IN'),
                    'device': {
                        'name': d[mac]['info']['device info']['label'],
                        'identifiers': ('eLan-thermometer-' + mac),
                        'connections': [["mac",  mac]],
                        'mf': 'Elko EP',
                        'mdl': d[mac]['info']['device info']['product type']
                    },
                    'device_class': 'temperature',
                    'state_topic': d[mac]['status_topic'],
                    'json_attributes_topic': d[mac]['status_topic'],
                    'value_template': '{{ value_json["temperature IN"] }}',
                    'unit_of_measurement': '°C'
                }
                mqtt_cli.publish('homeassistant/sensor/' + mac + '/IN/config',
                                bytearray(json.dumps(discovery), 'utf-8'))
                logger.info("Discovery 4.1. published for " + d[mac]['url'])
                logger.debug(json.dumps(discovery))

                discovery = {
                    'name': d[mac]['info']['device info']['label'] + '-OUT',
                    'unique_id': ('eLan-' + mac + '-OUT'),
                    'device': {
                        'name': d[mac]['info']['device info']['label'],
                        'identifiers': ('eLan-thermometer-' + mac),
                        'connections': [["mac",  mac]],
                        'mf': 'Elko EP',
                        'mdl': d[mac]['info']['device info']['product type']
                    },
                    'state_topic': d[mac]['status_topic'],
                    'json_attributes_topic': d[mac]['status_topic'],
                    'device_class': 'temperature',
                    'value_template': '{{ value_json["temperature OUT"] }}',
                    'unit_of_measurement': '°C'
                }
                mqtt_cli.publish('homeassistant/sensor/' + mac + '/OUT/config',
                                bytearray(json.dumps(discovery), 'utf-8'))

                logger.info("Discovery 4.2. published for " + d[mac]['url'])
                logger.debug(json.dumps(discovery))



            #
            # 5. Detectors
            #
            if ('detector' in d[mac]['info']['device info']['type']) or ('RFWD-' in d[mac]['info']['device info']['product type']) or ('RFSD-' in d[mac]['info']['device info']['product type']) or ('RFMD-' in d[mac]['info']['device info']['product type']) or ('RFSF-' in d[mac]['info']['device info']['product type']):
                logger.info(d[mac]['info']['device info'])

                icon = ''

                # A wild guess of icon
                if ('window' in d[mac]['info']['device info']['type']) or ('RFWD-' in d[mac]['info']['device info']['product type']):
                    icon = 'mdi:window-open'
                    if ('door' in str(d[mac]['info']['device info']['label']).lower()):
                        icon = 'mdi:door-open'

                if ('smoke' in d[mac]['info']['device info']['type']) or ('RFSD-' in d[mac]['info']['device info']['product type']):
                    icon = 'mdi:smoke-detector'

                if ('motion' in d[mac]['info']['device info']['type']) or ('RFMD-' in d[mac]['info']['device info']['product type']):
                    icon = 'mdi:motion-sensor'

                if ('flood' in d[mac]['info']['device info']['type']) or ('RFSF-' in d[mac]['info']['device info']['product type']):
                    icon = 'mdi:waves'


                # Silently expect that all detectors provide "detect" action
                discovery = {
                    'name': d[mac]['info']['device info']['label'],
                    'unique_id': ('eLan-' + mac),
                    'device': {
                        'name': d[mac]['info']['device info']['label'],
                        'identifiers' : ('eLan-detector-' + mac),
                        'connections': [["mac",  mac]],
                        'mf': 'Elko EP',
                        'mdl': d[mac]['info']['device info']['product type']
                    },
                    'state_topic': d[mac]['status_topic'],
                    'json_attributes_topic': d[mac]['status_topic'],
                    'value_template':
                    '{%- if value_json.detect -%}on{%- else -%}off{%- endif -%}'
                }

                if (icon != ''):
                    discovery['icon'] = icon

                mqtt_cli.publish('homeassistant/sensor/' + mac + '/config',
                                bytearray(json.dumps(discovery), 'utf-8'))

                logger.info("Discovery 5.1. published for " + d[mac]['url'])
                logger.debug(json.dumps(discovery))

                # Silently expect that all detectors provide "battery" status
                # Battery
                discovery = {
                    'name': d[mac]['info']['device info']['label'] + 'battery',
                    'unique_id': ('eLan-' + mac + '-battery'),
                    'device': {
                        'name': d[mac]['info']['device info']['label'],
                        'identifiers' : ('eLan-detector-' + mac),
                        'connections': [["mac",  mac]],
                        'mf': 'Elko EP',
                        'mdl': d[mac]['info']['device info']['product type']
                    },
                    'device_class': 'battery',
                    'state_topic': d[mac]['status_topic'],
                    'value_template':
                    '{%- if value_json.battery -%}100{%- else -%}0{%- endif -%}'
                }
                mqtt_cli.publish('homeassistant/sensor/' + mac + '/battery/config',
                                bytearray(json.dumps(discovery), 'utf-8'))

                logger.info("Discovery 5.2. published for " + d[mac]['url'])
                logger.debug(json.dumps(discovery))


                # START - RFWD window/door detector
                if (d[mac]['info']['device info']['product type'] == 'RFWD-100') or (d[mac]['info']['device info']['product type'] == 'RFSF-1B'):
                    # Alarm
                    discovery = {
                        'name': d[mac]['info']['device info']['label'] + 'alarm',
                        'unique_id': ('eLan-' + mac + '-alarm'),
                        'icon': 'mdi:alarm-light',
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers' : ('eLan-detector-' + mac),
                            'connections': [["mac",  mac]],
                            'mf': 'Elko EP',
                            'mdl': d[mac]['info']['device info']['product type']
                        },
                        'state_topic': d[mac]['status_topic'],
                        'json_attributes_topic': d[mac]['status_topic'],
                        'value_template':
                        '{%- if value_json.alarm -%}on{%- else -%}off{%- endif -%}'
                    }
                    mqtt_cli.publish('homeassistant/sensor/' + mac + '/alarm/config',
                                    bytearray(json.dumps(discovery), 'utf-8'))

                    logger.info("Discovery 5.3. published for " + d[mac]['url'])
                    logger.debug(json.dumps(discovery))

                if (d[mac]['info']['device info']['product type'] == 'RFWD-100'):
                    # Tamper
                    discovery = {
                        'name': d[mac]['info']['device info']['label'] + 'tamper',
                        'unique_id': ('eLan-' + mac + '-tamper'),
                        'icon': 'mdi:gesture-tap',
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers' : ('eLan-detector-' + mac),
                            'connections': [["mac",  mac]],
                            'mf': 'Elko EP',
                            'mdl': d[mac]['info']['device info']['product type']
                        },
                        'state_topic': d[mac]['status_topic'],
                        'json_attributes_topic': d[mac]['status_topic'],
                        'value_template':
                        '{%- if value_json.tamper == "opened" -%}on{%- else -%}off{%- endif -%}'
                    }
                    mqtt_cli.publish('homeassistant/sensor/' + mac + '/tamper/config',
                                    bytearray(json.dumps(discovery), 'utf-8'))

                    logger.info("Discovery 5.4. published for " + d[mac]['url'])
                    logger.debug(json.dumps(discovery))

                    # Automat
                    discovery = {
                        'name': d[mac]['info']['device info']['label'] + 'automat',
                        'unique_id': ('eLan-' + mac + '-automat'),
                        'icon': 'mdi:arrow-decision-auto',
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers' : ('eLan-detector-' + mac),
                            'connections': [["mac",  mac]],
                            'mf': 'Elko EP',
                            'mdl': d[mac]['info']['device info']['product type']
                        },
                        'state_topic': d[mac]['status_topic'],
                        'json_attributes_topic': d[mac]['status_topic'],
                        'value_template':
                        '{%- if value_json.automat -%}on{%- else -%}off{%- endif -%}'
                    }
                    mqtt_cli.publish('homeassistant/sensor/' + mac + '/automat/config',
                                    bytearray(json.dumps(discovery), 'utf-8'))

                    logger.info("Discovery 5.5. published for " + d[mac]['url'])
                    logger.debug(json.dumps(discovery))

                    # Disarm
                    discovery = {
                        'name': d[mac]['info']['device info']['label'] + 'disarm',
                        'unique_id': ('eLan-' + mac + '-disarm'),
                        'icon': 'mdi:lock-alert',
                        'device': {
                            'name': d[mac]['info']['device info']['label'],
                            'identifiers' : ('eLan-detector-' + mac),
                            'connections': [["mac",  mac]],
                            'mf': 'Elko EP',
                            'mdl': d[mac]['info']['device info']['product type']
                        },
                        'state_topic': d[mac]['status_topic'],
                        'json_attributes_topic': d[mac]['status_topic'],
                        'value_template':
                        '{%- if value_json.disarm -%}on{%- else -%}off{%- endif -%}'
                    }
                    mqtt_cli.publish('homeassistant/sensor/' + mac + '/disarm/config',
                                    bytearray(json.dumps(discovery), 'utf-8'))

                    logger.info("Discovery 5.6. published for " + d[mac]['url'])
                    logger.debug(json.dumps(discovery))

                # END - RFWD window/door detector




    async def process_command(topic, data):
        try:
            tmp = topic.split('/')
            # check if it is one of devices we know
            if (tmp[0] == 'eLan') and (tmp[2] == 'command') and (tmp[1] in d):
                data = json.loads(data)
                resp = await session.put(d[tmp[1]]['url'], json=data)
                info = await resp.text()
                # check and publish updated state of device
                await publish_status(tmp[1])
        except:
            logger.error("Unexpected error:", sys.exc_info()[0])

    async def login(name, password):
        hash = hashlib.sha1(password).hexdigest()
        credentials = {
        'name': name,
        'key': hash
        }

        logger.info("Get main/login page (to get cookies)")
        resp = await session.get(args.elan_url + '/', timeout=3)

        logger.info("Are we already authenticated? E.g. API check")
        resp = await session.get(args.elan_url + '/api', timeout=3)

        not_logged = True

        while not_logged:
            if resp.status != 200:
                logger.info("Authenticating to eLAN")
                resp = await session.post(args.elan_url + '/login',data=credentials)

            time.sleep(1)
            logger.info("Getting eLan device list")
            resp = await session.get(args.elan_url + '/api/devices', timeout=3)
            if  resp.status == 200:
                not_logged = False



    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.connected_flag = True
            logger.info("Connected to MQTT broker")
        else:
            logger.error("Bad connection Returned code = " + str(rc))

    def on_disconnect(client, userdata, rc):
        logging.info("MQTT broker disconnected. Reason: " + str(rc))
        mqtt_cli.connected_flag = False

    def on_message(client, userdata, message):
        logging.info("MQTT broker message. " + str(message.topic))
        pending_message.append(message)

    # setup mqtt
    mqtt.Client.connected_flag = False
    mqtt_cli = mqtt.Client("eLan2MQTT_main_worker" + args.mqtt_id)
    logger.info("Connecting to MQTT broker")
    logger.info(args.mqtt_broker)


    mqtt_broker = args.mqtt_broker
    i = mqtt_broker.find('mqtt://')
    if i<0:
        raise Exception('MQTT URL not provided!')

    # Strip mqtt header from URL
    mqtt_broker = mqtt_broker[7:]

    i = mqtt_broker.find('@')
    mqtt_username = ""
    mqtt_password = ""

    # parse MQTT URL
    if (i>0):
        # We have credentials
        mqtt_username = mqtt_broker[0:i]
        mqtt_broker = mqtt_broker[i+1:]
        i = mqtt_username.find(':')
        if (i>0):
            # We have password
            mqtt_password = mqtt_username[i+1:]
            mqtt_username = mqtt_username[0:i]

    mqtt_cli.username_pw_set(username=mqtt_username, password=mqtt_password)
    # bind call back functions
    mqtt_cli.on_connect = on_connect
    mqtt_cli.on_disconnect = on_disconnect
    mqtt_cli.on_message = on_message
    mqtt_cli.connect(mqtt_broker, 1883, 120)
    mqtt_cli.loop_start()

    # Let's give MQTT some time to connect
    time.sleep(5)

    # wait for connection
    if not mqtt_cli.connected_flag:
        raise Exception('MQTT not connected!')


    logger.info("Connected to MQTT broker")

    # Connect to eLan and
    cookie_jar = aiohttp.CookieJar(unsafe=True)
    session = aiohttp.ClientSession(cookie_jar=cookie_jar)
    # authentication to eLAN
    await login(args.elan_user[0],str(args.elan_password[0]).encode('cp1250'))

    # Get list of devices
    logger.info("Getting eLan device list")
    resp = await session.get(args.elan_url + '/api/devices', timeout=3)
    device_list = await resp.json()

    logger.info("Devices defined in eLan:\n" + str(device_list))

    for device in device_list:
        resp = await session.get(device_list[device]['url'], timeout=3)
        info = await resp.json()
        device_list[device]['info'] = info

        if "address" in info['device info']:
            mac = str(info['device info']['address'])
        else:
            mac = str(info['id'])
            logger.error("There is no MAC for device " + str(device_list[device]))
            device_list[device]['info']['device info']['address'] = mac

        logger.info("Setting up " + device_list[device]['url'])

        d[mac] = {
            'info': info,
            'url': device_list[device]['url'],
            'status_topic': ('eLan/' + mac + '/status'),
            'control_topic': ('eLan/' + mac + '/command')
        }

        logger.info("Subscribing to control topic " + d[mac]['control_topic'])
        mqtt_cli.subscribe(d[mac]['control_topic'])
        logger.info("Subscribed to " + d[mac]['control_topic'])

        if args.disable_autodiscovery==True:
            logger.info("Autodiscovery disabled")
        else:
            await publish_discovery(mac)

        await publish_status(mac)

    i = 0
    try:
        discovery_interval = 10 * 60
        info_interval = 1 * 60
        last_discovery = time.time()
        last_info = time.time()
        while True:
            if ((time.time() - last_info) > info_interval):
                try:
                    last_info = time.time()
                    if ((time.time() - last_discovery) > discovery_interval):
                        last_discovery = time.time()
                        for device in device_list:
                            mac = str(device_list[device]['info'][
                                'device info']['address'])
                            if args.disable_autodiscovery==True:
                                logger.info("Autodiscovery disabled")
                            else:
                                await publish_discovery(mac)

                    for device in device_list:
                        mac = str(device_list[device]['info']['device info'][
                            'address'])
                        await publish_status(mac)

                except asyncio.TimeoutError:
                    pass
                    time.sleep(0.1)
            try:
                while (len(pending_message) > 0):
                    message_to_process = pending_message.pop(0)
                    logger.info("Processing command from topic: " + message_to_process.topic)
                    logger.info(
                        "Command: " + str(message_to_process.payload.decode("utf-8")))
                    await process_command(message_to_process.topic, str(message_to_process.payload.decode("utf-8")))
                    i = i + 1
            except:
                pass

            time.sleep(0.1)

        logger.error("MAIN WORKER: Should not ever reach here")
        await mqtt_cli.disconnect()
    except ClientException as ce:
        logger.error("MAIN WORKER: Client exception: %s" % ce)
        try:
            await mqtt_cli.disconnect()
        except:
            pass
        time.sleep(5)


def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument(
        'elan_url', metavar='elan-url', help='URL of eLan (http://x.x.x.x/)')
    parser.add_argument(
        '-elan-user',
        metavar='elan_user',
        nargs=1,
        default='admin',
        dest='elan_user',
        help='username for eLan login')
    parser.add_argument(
        '-elan-password',
        metavar='elan_password',
        nargs=1,
        dest='elan_password',
        default='elkoep',
        help='password for eLan login')
    parser.add_argument(
        'mqtt_broker',
        metavar='mqtt-broker',
        help='MQTT broker (mqtt://user:password@x.x.x.x))')
    parser.add_argument(
        '-log-level',
        metavar='log_level',
        nargs=1,
        dest='log_level',
        default='warning',
        help='Log level debug|info|warning|error|fatal')
    parser.add_argument(
        '-disable-autodiscovery',
        metavar='disable_autodiscovery',
        nargs='?',
        dest='disable_autodiscovery',
        default=False,
        type=str2bool,
        help='Disable autodiscovery True|False')
    parser.add_argument(
        '-mqtt-id',
        metavar='mqtt_id',
        nargs=1,
        dest='mqtt_id',
        default='',
        help='Client ID presented to MQTT server')

    args = parser.parse_args()

    formatter = "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    numeric_level = getattr(logging, args.log_level[0].upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = 30
    logging.basicConfig(level=numeric_level, format=formatter)

    while True:
        try:
            asyncio.run(main())
        except:
            logger.exception(
                "MAIN WORKER: Something went wrong. But don't worry we will start over again."
            )
            logger.error("But at first take some break. Sleeping for 10 s")
            time.sleep(10)
