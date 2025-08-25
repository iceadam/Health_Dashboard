const express = require("express");
const cors = require("cors");
const mysql = require("mysql2");

const app = express();
const port = 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Database Connection
const db = mysql.createConnection({
  host: "localhost",
  user: "root", // Replace with your DB username
  password: "root1234", // Replace with your DB password
  database: "iot_health_monitor" // Replace with your DB name
});

// Connect to the database
db.connect((err) => {
  if (err) {
    console.error("Database connection failed:", err.message);
    process.exit(1); // Exit if the connection fails
  }
  console.log("Connected to the database.");
});

// Endpoint to Update Blue LED State (from index.html)
app.post("/controlBlueLed", (req, res) => {
  const { state } = req.body; // Extract 'state' from the request body

  if (state !== "on" && state !== "off") {
    return res.status(400).json({ success: false, message: "Invalid LED state" });
  }

  // Update the state and database
  const timestamp = new Date().toISOString();
  const color = state === "on" ? "blue_on" : "blue_off";

  const query = "INSERT INTO rgb_led_status (timestamp, color) VALUES (?, ?)";
  db.execute(query, [timestamp, color], (err, result) => {
    if (err) {
      console.error("Failed to update LED status in the database:", err.message);
      return res.status(500).json({ success: false, message: "Database error" });
    }

    console.log("LED status updated in the database:", result);
    return res.json({ success: true, message: `Blue LED turned ${state}` });
  });
});

// Endpoint to Get Blue LED State (Optional for Debugging or Display)
app.get("/blueLedState", (req, res) => {
  const query = "SELECT * FROM rgb_led_status ORDER BY id DESC LIMIT 1";

  db.execute(query, (err, results) => {
    if (err) {
      console.error("Failed to fetch LED status from the database:", err.message);
      return res.status(500).json({ success: false, message: "Database error" });
    }

    if (results.length > 0) {
      return res.json({ success: true, data: results[0] });
    } else {
      return res.json({ success: false, message: "No data available" });
    }
  });
});

// Endpoint to Fetch Sensor Data for the Dashboard
app.get("/sensorData", (req, res) => {
  const query = "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1";

  db.execute(query, (err, results) => {
    if (err) {
      console.error("Failed to fetch sensor data:", err.message);
      return res.status(500).json({ success: false, message: "Database error" });
    }

    if (results.length > 0) {
      const data = results[0];
      const accelMagnitude = Math.sqrt(
        Math.pow(data.accel_x, 2) +
        Math.pow(data.accel_y, 2) +
        Math.pow(data.accel_z, 2)
      );

      return res.json({
        success: true,
        bodyTemp: { value: data.body_temp, status: data.body_temp > 37 ? "Alert" : "Normal" },
        ambientTemp: { value: data.ambient_temp, status: data.ambient_temp > 30 ? "Alert" : "Normal" },
        movement: {
          x: data.accel_x,
          y: data.accel_y,
          z: data.accel_z,
          magnitude: accelMagnitude.toFixed(2), // Include the calculated magnitude
          status: accelMagnitude > 9.0 ? "Alert" : "Normal" // Example threshold for alerts
        }
      });
    } else {
      return res.json({ success: false, message: "No sensor data available" });
    }
  });
});

// Endpoint to Fetch Historical Data for the Chart
app.get("/historicalData", (req, res) => {
  const query = "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 50";

  db.execute(query, (err, results) => {
    if (err) {
      console.error("Failed to fetch historical data:", err.message);
      return res.status(500).json({ success: false, message: "Database error" });
    }

    const data = results.map(row => {
      const accelMagnitude = Math.sqrt(
        Math.pow(row.accel_x, 2) +
        Math.pow(row.accel_y, 2) +
        Math.pow(row.accel_z, 2)
      );

      return {
        timestamp: row.timestamp,
        bodyTemp: row.body_temp,
        ambientTemp: row.ambient_temp,
        movement: {
          x: row.accel_x,
          y: row.accel_y,
          z: row.accel_z,
          magnitude: accelMagnitude.toFixed(2) // Include the calculated magnitude
        }
      };
    });

    return res.json(data);
  });
});

// Start the server
app.listen(port, () => {
  console.log(`Server is running on http://127.0.0.1:${port}`);
});
