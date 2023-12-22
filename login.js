document.getElementById('login-form').addEventListener('submit', function(event) {
  event.preventDefault(); // Prevent the form from being submitted normally

  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;

  const options = {
    username: username,
    password: password,
    protocol: 'wss',
    port: 8884,
    path: '/mqtt',
  };

  const client = mqtt.connect('tls://95ea70d6edb34e4a956c8f346ae8fba8.s1.eu.hivemq.cloud:8884', options);

  client.on('connect', () => {
    console.log('Connected!');
    // If connected successfully, redirect to the main page
    window.location.href = 'main.html';
  });

  client.on('error', (error) => {
    console.log('Error:', error);
    // If there is an error, show an alert
    alert('Failed to connect. Please check your username and password.');
  });
});
