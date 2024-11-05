import express from 'express'
import mqtt from 'mqtt'
import WebSocket from 'ws'
import { exec } from "child_process";
import { spawn } from 'child_process';
import * as child from 'child_process';
import fs from 'node:fs';
import cors from 'cors'
import convert from 'xml-js';
// const XmlStream = require('xml-stream');
import XmlStream from 'xml-stream';

const app = express()
app.use(express.json())
app.use(cors())




const mqttUrl = 'mqtt://127.0.0.1:1883'; // Example broker
const clientId = 'client' + Math.random().toString(36).substring(7)
const connectOpt= {
    keepalive: 60,
    clientId: clientId,
    protocolId: 'MQTT',
    protocolVersion: 4,
    clean: true,
    reconnectPeriod: 1000,
    connectTimeout: 30*1000,
}
const client = mqtt.connect(mqttUrl, connectOpt);




client.on('connect', () => {
  console.log('Connected to MQTT broker');
  
  // Subscribe to a topic
  client.subscribe('uploader', (err) => {
    if (!err) {
      console.log('Subscribed to topic: uploader');
    }
  });
});




client.on('message', (topic, message) => {
  // console.log(`Received message on ${topic}: ${message.toString()}`);
  const msg = message.toString();
  console.log(`Received message on ${topic}: ${msg}`);
  
  // Broadcast the message to all connected WebSocket clients
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({ topic, msg }));
    }
  });
});



// Currently Incoming msg handled using WebSocket
app.post('/publish', (req, res) => {
  const { topic, message } = req.body;
  
  if (!topic || !message) {
    return res.status(400).send('Topic and message are required');
  }

  client.publish(topic, message, (err) => {
    if (err) {
      return res.status(500).send('Error publishing message');
    }
    res.status(200).send(`Message published to ${topic}`);
  });

});



app.get('/', (req, res) => {
  res.send('Hello World!')
})

app.post('/executeScript', (req, res) => {
  // const { exec } = require("child_process");
  console.log('Executing Script')
  console.log(req.body)


  const command = 'python3';
  const args = [
      'convert.py',
      '--inst', '50',
      '--loc', '28.54503', '77.19367',
      '--animeid', '6894',
      '--diff', '0'
  ];

  // Spawn the child process
  const child = spawn(command, args, { cwd: '/home/chetan/Downloads/ex' });

  // Handle stdout
  child.stdout.on('data', (data) => {
      console.log(`Output: ${data.toString()}`);
      wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          let output = data.toString()
          const progressMatch = output.match(/Progress\s*=\s*(\d+(\.\d+)?)\s*%/);
          const progress = progressMatch ? parseFloat(progressMatch[1]) : null;
          client.send(JSON.stringify(progress));
        }
      });
  });

  // Handle stderr
  child.stderr.on('data', (data) => {
      console.error(`Error: ${data.toString()}`);
  });

  // Handle process exit
  child.on('exit', (code) => {
    fs.readFile('/home/chetan/Downloads/ex/paths/takeoff_points.kml', 'utf8', (err, data) => {
      if (err) {
        console.error(err);
        return;
      }
      let initialMarkers = [];
      var result = JSON.parse(convert.xml2json(data, {compact: true, spaces: 4}));
      for(var i = 0; i < result.kml.Document.Placemark.length; i++){
        var results = result.kml.Document.Placemark[i].Point.coordinates._text;
        var coord = results.split(",");
        var latitude = coord[1];
        var longitude = coord[0];
        console.log("lat/long: " + latitude + ", " + longitude);
        initialMarkers.push({id:i, longitude:Number(longitude), latitude:Number(latitude)});
      }
      // initialMarkers.push({id:id, longitude:lng, latitude:lat});
      console.log('sending initial markers')
      res.send(initialMarkers);
  
    });
  });
})

app.get('/getAnimationPoints',(req,res)=>{
  // console.log('Getting Animation Points')
  const xmlFilePath = '/home/chetan/Downloads/ex/paths/complete_paths.kml'; // Update with your file path
    const stream = fs.createReadStream(xmlFilePath);
    const xmlStream = new XmlStream(stream);
    const result = [];

    xmlStream.on('endElement: Placemark', (item) => {
        // Collect desired data from each Placemark
        if (item.LineString && item.LineString.coordinates) {
          const coords = item.LineString.coordinates.trim().split(' ').map(coord => {
              const [lng, lat] = coord.split(',').map(Number); // Convert to numbers
              return { lng, lat };
          });
          console.log(coords)
  
          result.push({
              name: item.name,
              coordinates: coords,
              // Add any other properties you need
          });
      } else {
          console.warn('No LineString coordinates found for:', item.name);
      }
    });

    xmlStream.on('end', () => {
        // Send the parsed result to the frontend
        console.log('completed parsing')
        let formatedData = result.map((d)=>d.coordinates)
        // setMarkers(data);
        let finalData=[];
        formatedData.forEach(elements => {
          elements.forEach((ele,id)=>{
            finalData.push([ele.lng, ele.lat])
          })
        });
        // res.json(finalData);
        console.log(finalData.length)
        console.log(finalData[0])
        const convexHull = calculateConvexHull(finalData);
        res.json(convexHull);
    });

    xmlStream.on('error', (err) => {
        console.error('Error parsing XML:', err);
        res.status(500).send('Error parsing XML');
    })
})


const server = app.listen(8000, () => {
  console.log('Server is running on port 8000')
})

const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
  console.log('New WebSocket connection');

  ws.on('message', (message) => {
    console.log(`Received from client: ${message}`);
    client.publish("broadcast", JSON.stringify({"source": 0, "destination": 255, "messageid": 1, "payload": {}}))
    client.publish("uploader", JSON.stringify({"source": 0, "destination": 255, "messageid": 1, "payload": {}}))
  });

  ws.on('close', () => {
    console.log('WebSocket connection closed');
  });
});



// util function
function calculateConvexHull(points) {
  // Sort points by x-coordinate, and then by y-coordinate to break ties
  points.sort((a, b) => {
      if (a[0] === b[0]) return a[1] - b[1];
      return a[0] - b[0];
  });

  // Helper function to compute the cross product of vectors OA and OB
  // A positive cross product indicates a counter-clockwise turn, 0 indicates a collinear point, and negative indicates a clockwise turn
  function cross(o, a, b) {
      return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  }

  // Build the lower hull
  const lower = [];
  for (let point of points) {
      while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) {
          lower.pop();
      }
      lower.push(point);
  }

  // Build the upper hull
  const upper = [];
  for (let i = points.length - 1; i >= 0; i--) {
      while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], points[i]) <= 0) {
          upper.pop();
      }
      upper.push(points[i]);
  }

  // Remove the last point of each hull because it's repeated at the beginning of the other hull
  lower.pop();
  upper.pop();

  // Concatenate lower and upper hull to get the full convex hull
  return [...lower, ...upper];
}

// Example: Generating 800,000 random points
const points = [];
for (let i = 0; i < 800000; i++) {
  points.push([Math.random() * 360 - 180, Math.random() * 180 - 90]); // Random points in long-lat range
}

// Compute the convex hull
const convexHull = calculateConvexHull(points);

// The convex hull is now in `convexHull` and can be used to draw the outline or further analyze.
console.log(convexHull);
