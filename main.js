// Function to publish a message every 5 seconds
function publishMessage() {
  if (client) {
    client.publish('Kanyon/mqtt_request', '1');
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

    // Update the text content of the corresponding element
    document.getElementById(elementId).textContent = fieldLabel + ': ' + String.fromCharCode.apply(null, message) + units;

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
client.subscribe('Kanyon/Temp');
client.subscribe('Kanyon/LV_soc');
client.subscribe('Kanyon/LV_Voltage');

// Set up an interval to call the publishMessage function every 5 seconds (5000 milliseconds)
setInterval(publishMessage, 5000);
