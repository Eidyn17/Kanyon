// Function to publish a message every 5 seconds with a message expiry of 10 seconds
function publishMessage() {
  if (navigator.onLine) {
    if (client) {
      const messageOptions = {
        properties: {
          messageExpiryInterval: 10, // Expiry time in seconds
        },
      };

      client.publish('Kanyon/mqtt_request', '1', messageOptions);
      console.log('MQTT Request Sent.');
    }
  } else {
    console.log('Not connected to the internet. Message not sent.');
  }
}

  // Variable to store the last update time
  let lastUpdateTime = '';  

  // Function to update the message display
  function updateMessageDisplay(topic, message) {
    // Get the corresponding element based on the topic
    var elementId;
    var fieldLabel;
    
    switch (topic) {
      case 'Kanyon/HV_Voltage':
        elementId = 'hv-voltage';
        fieldLabel = 'HV Voltage';
        break;
      case 'Kanyon/HV_SOC':
        elementId = 'hv-soc';
        fieldLabel = 'HV SoC';
        break;
      case 'Kanyon/DC-DC_Current':
        elementId = 'dc-dc_current';
        fieldLabel = 'DC-DC Current';
        break;
      case 'Kanyon/DC-DC_Power':
        elementId = 'dc-dc_power';
        fieldLabel = 'DC-DC Power';
        break;
      case 'Kanyon/LV_Voltage':
        elementId = 'lv-voltage';
        fieldLabel = 'LV Voltage';
        break;
      case 'Kanyon/LV_soc':
        elementId = 'lv-soc';
        fieldLabel = 'LV SOC';
        break;
      case 'Kanyon/Temp':
        elementId = 'temperature';
        fieldLabel = 'Temperature';
        break;
      case 'Kanyon/DC-DC_Status':
        elementId = 'dc-dc_status';
        fieldLabel = 'DC-DC Status';
        break;
      case 'Kanyon/Heater_Status':
        elementId = 'heater_status';
        fieldLabel = 'Battery Heater Status';
        break;
      case 'Kanyon/log':
        elementId = 'log-content'; // The id of the "Log" section
        fieldLabel = 'Log'; // Label for the new section
        break;
      default:
        // Ignore other topics
        return;
    }
    // Update last update time
    lastUpdateTime = new Date().toLocaleString();
    document.getElementById('last-update').textContent = 'Last update received: ' + lastUpdateTime;

    // Append units based on the topic
    var units = '';
    switch (topic) {
      case 'Kanyon/HV_Voltage':
        units = ' V';
        break;
      case 'Kanyon/HV_SOC':
        units = ' %';
        break;
      case 'Kanyon/DC-DC_Current':
        units = ' mA';
        break;
      case 'Kanyon/DC-DC_Power':
        units = ' mW';
        break;
      case 'Kanyon/Temp':
        units = ' °C';
        break;
      case 'Kanyon/LV_Voltage':
        units = ' mV';
        break;
      case 'Kanyon/LV_soc':
        units = ' %';
        break;
    }

    // Handle message conversion: check if it's an ArrayBuffer, else treat as string
    let displayMessage;
    if (message instanceof ArrayBuffer) {
      displayMessage = String.fromCharCode.apply(null, new Uint8Array(message));
    } else {
      displayMessage = message.toString();
    }

    // For topics with numeric values, round them to 2 decimal places
    if (topic !== 'Kanyon/log' && topic !== 'Kanyon/DC-DC_Status' && topic !== 'Kanyon/Heater_Status') {
      let roundedValue = parseFloat(displayMessage).toFixed(2);
      document.getElementById(elementId).textContent = fieldLabel + ': ' + roundedValue + units;
    } else if (topic === 'Kanyon/DC-DC_Status' || topic === 'Kanyon/Heater_Status') {
      // Handle ON/OFF messages for these topics
      let statusMessage = (displayMessage === 'ON') ? 'ON' : 'OFF';
      document.getElementById(elementId).textContent = fieldLabel + ': ' + statusMessage;
    } else {
      // For 'Kanyon/log', just display the message as-is
      document.getElementById(elementId).textContent = fieldLabel + ': ' + displayMessage;
    }
  }

// prints a received message
client.on('message', function(topic, message) {
  console.log(String.fromCharCode.apply(null, message)); // need to convert the byte array to string
  // Call the updateMessageDisplay function with the received topic and message
  updateMessageDisplay(topic, message);
});

// prints an error message
client.on('error', (error) => {
  console.log('Error:', error);
});

// subscribe to topics
client.subscribe('Kanyon/HV_Voltage');
client.subscribe('Kanyon/HV_SOC');
client.subscribe('Kanyon/DC-DC_Current');
client.subscribe('Kanyon/DC-DC_Power');
client.subscribe('Kanyon/Temp');
client.subscribe('Kanyon/LV_soc');
client.subscribe('Kanyon/LV_Voltage');
client.subscribe('Kanyon/DC-DC_Status');
client.subscribe('Kanyon/Heater_Status');
client.subscribe('Kanyon/log');

// Set up an interval to call the publishMessage function every 5 seconds (5000 milliseconds)
setInterval(publishMessage, 5000);

// First load of values
publishMessage()
