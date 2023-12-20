const options = {
  username: 'Eidyn',
  password: 'Mqtt1111',
  protocol: 'wss', // Specify the WebSocket protocol
  port: 8884,      // Specify the port for WSS
  path: '/mqtt',   // Specify the WebSocket path
};

const client = mqtt.connect('tls://95ea70d6edb34e4a956c8f346ae8fba8.s1.eu.hivemq.cloud:8884', options);

// prints a received message
client.on('message', function(topic, message) {
  console.log(String.fromCharCode.apply(null, message)); // need to convert the byte array to string
});

// reassurance that the connection worked
client.on('connect', () => {
  console.log('Connected!');
});

// prints an error message
client.on('error', (error) => {
  console.log('Error:', error);
});

// subscribe and publish to the same topic
client.subscribe('Kanyon/HV_Voltage');
client.publish('Kanyon/mqtt_request', '1');
