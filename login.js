const options = {
  username: 'Eidyn',
  password: 'Mqtt1111',
  protocol: 'wss', // Specify the WebSocket protocol
  port: 8884,      // Specify the port for WSS
  path: '/mqtt',   // Specify the WebSocket path
};

const client = mqtt.connect('tls://95ea70d6edb34e4a956c8f346ae8fba8.s1.eu.hivemq.cloud:8884', options);

// reassurance that the connection worked
client.on('connect', () => {
  console.log('Connected!');
});
