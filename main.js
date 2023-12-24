// Function to publish a message every 5 seconds
function publishMessage() {
    if (navigator.onLine) {
      if (client) {
        client.publish('Kanyon/mqtt_request', '1');
        console.log('MQTT Request Sent.');
      }
    } else {
      console.log('Not connected to the internet. Message not sent.');
    }
  }
  
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
        default:
          // Ignore other topics
          return;
      }
  
      // Append units based on the topic
      var units = '';
      switch (topic) {
        case 'Kanyon/HV_Voltage':
          units = ' V';
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
  
      // Convert the message to a string and round to 2 decimal places
      var roundedValue = parseFloat(String.fromCharCode.apply(null, message)).toFixed(2);
  
      // Update the text content of the corresponding element
      document.getElementById(elementId).textContent = fieldLabel + ': ' + roundedValue + units;
  
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
  client.subscribe('Kanyon/DC-DC_Current');
  client.subscribe('Kanyon/DC-DC_Power');
  client.subscribe('Kanyon/Temp');
  client.subscribe('Kanyon/LV_soc');
  client.subscribe('Kanyon/LV_Voltage');
  
  // Set up an interval to call the publishMessage function every 5 seconds (5000 milliseconds)
  setInterval(publishMessage, 5000);
  
  // First load of values
  publishMessage()
