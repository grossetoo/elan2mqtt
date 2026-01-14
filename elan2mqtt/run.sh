#!/usr/bin/with-contenv bashio

echo "🟢 Starting Elan2MQTT add-on..."

# Read configuration from Home Assistant
CONFIG_PATH=/data/options.json

if bashio::fs.file_exists "${CONFIG_PATH}"; then
    echo "✅ Configuration file exists"
else
    echo "❌ Configuration file not found!"
    exit 1
fi

ELAN_URL=$(bashio::config 'eLanURL')
MQTT_SERVER=$(bashio::config 'MQTTserver')
USERNAME=$(bashio::config 'username')
PASSWORD=$(bashio::config 'password')
LOG_LEVEL=$(bashio::config 'log_level')
DISABLE_AUTODISCOVERY=$(bashio::config 'disable_autodiscovery')
MQTT_ID=$(bashio::config 'mqtt_id')

echo "🔧 Configuration loaded:"
echo "  eLAN URL: ${ELAN_URL}"
echo "  MQTT Server: [configured]"
echo "  Username: ${USERNAME}"
echo "  Log Level: ${LOG_LEVEL}"
echo "  Disable Autodiscovery: ${DISABLE_AUTODISCOVERY}"

# Change to app directory
cd /elan2mqtt-2.0.0

# Activate virtual environment
. venv/bin/activate

# Build command
CMD="python main_worker.py ${ELAN_URL} -elan-user ${USERNAME} -elan-password ${PASSWORD} ${MQTT_SERVER} -log-level ${LOG_LEVEL}"

if [ "${DISABLE_AUTODISCOVERY}" = "true" ]; then
    CMD="${CMD} -disable-autodiscovery True"
fi

if [ -n "${MQTT_ID}" ]; then
    CMD="${CMD} -mqtt-id ${MQTT_ID}"
fi

echo "🚀 Starting eLAN MQTT Gateway..."

# Run the Python script
exec ${CMD}
