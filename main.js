// Function to authenticate and connect
function authenticateAndConnect(event) {
  // Prevent the default form submission behavior
  event.preventDefault();

  // Get the username and password from the form
  var username = document.getElementById('username').value;
  var password = document.getElementById('password').value;

  // Get the message container
  var messageContainer = document.getElementById('message-container');

  // Check if username and password are not empty
  if (username && password) {
    // Connect to MQTT broker with the provided credentials
    connectToBroker(username, password);
  } else {
    // Display a message for incorrect login details
    showMessage('Please enter both username and password.', 'error');

    // Clear the input fields
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
  }
}

// Attach the event listener to the form
document.getElementById('login-form-container').addEventListener('submit', authenticateAndConnect);

// Function to display messages
function showMessage(message, messageType) {
  var messageContainer = document.getElementById('message-container');
  messageContainer.innerHTML = message;

  // Optionally, you can add styling or classes based on the message type
  if (messageType === 'error') {
    messageContainer.style.color = 'red';
  }

  // Clear the message after a delay (e.g., 3 seconds)
  setTimeout(function () {
    messageContainer.innerHTML = '';
    messageContainer.style.color = ''; // Reset the style
  }, 3000);
}

// Function to connect to the MQTT broker
function connectToBroker(username, password) {
  const options = {
    username: username,
    password: password,
    protocol: 'wss',
    port: 8884,
    path: '/mqtt',
  };

  // Use 'var' to declare the variable in the local scope
  var client = mqtt.connect('tls://95ea70d6edb34e4a956c8f346ae8fba8.s1.eu.hivemq.cloud:8884', options);

  // Variable to hold the interval ID
  var intervalId;

  // Flag to check if the unauthorized message has been displayed
  var unauthorizedMessageDisplayed = false;

  // prints an error message
  client.on('error', (error) => {
    // Check if the error is due to unauthorized access
    if (error && error.code === 4 && !unauthorizedMessageDisplayed) {
      // Display a message for unauthorized access
      showMessage('Unauthorized. Please check your credentials.', 'error');

      // Clear the input fields
      document.getElementById('username').value = '';
      document.getElementById('password').value = '';

      // Clear the interval
      clearInterval(intervalId);

      // Set the flag to true to prevent displaying the message multiple times
      unauthorizedMessageDisplayed = true;
    } else {
      // For other errors, log to console and display a generic message
      console.log('Error:', error);
      showMessage('An error occurred. Please try again.', 'error');
    }
  });

  // reassurance that the connection worked
  client.on('connect', () => {
    console.log('Connected!');

    // subscribe to topics
    client.subscribe('Kanyon/HV_Voltage');
    client.subscribe('Kanyon/Temp');
    client.subscribe('Kanyon/LV_soc');
    client.subscribe('Kanyon/LV_Voltage');

    // Set up an interval to call the publishMessage function every 5 seconds (5000 milliseconds)
    intervalId = setInterval(publishMessage, 5000);

    // Hide the login form and show the content
    document.getElementById('login-form-container').style.display = 'none';
    document.getElementById('content').style.display = 'block';
  });

  // prints a received message
  client.on('message', function (topic, message) {
    console.log(String.fromCharCode.apply(null, message)); // need to convert the byte array to string
    updateMessageDisplay(topic, message);
  });

  // Function to publish a message every 5 seconds
  function publishMessage() {
    client.publish('Kanyon/mqtt_request', '1');
  }
}

// Add an event listener for 'keydown' on the password input field
document.getElementById('password').addEventListener('keydown', function (event) {
  // Check if the pressed key is 'Enter'
  if (event.key === 'Enter') {
    // Prevent the default form submission behavior
    event.preventDefault();
    // Trigger the authenticateAndConnect function
    authenticateAndConnect();
  }
});


