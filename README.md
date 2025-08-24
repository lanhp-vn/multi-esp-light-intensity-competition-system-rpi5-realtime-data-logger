# Multi-ESP Light Intensity Competition System with Raspberry Pi 5 Real-Time Data Logger

A distributed IoT system where three ESP8266 devices compete for master status based on light intensity readings, with real-time data visualization and logging on a Raspberry Pi 5.

## Demo Video

A demonstration of the system in operation is available at: [https://youtu.be/oAh9-jO0_ec](https://youtu.be/oAh9-jO0_ec)

## System Overview

This system implements a competitive swarm behavior where three ESP8266 devices equipped with light sensors compete to become the "master" device based on their light intensity readings. The device with the highest light reading becomes the master and communicates its status to a Raspberry Pi 5, which provides real-time data visualization and logging.

### Key Features

- **Competitive Swarm Behavior**: Three ESP8266 devices compete for master status
- **Real-time Data Visualization**: Live graphs showing light readings and master durations
- **Automatic Data Logging**: Timestamped logs of all device activities
- **System Reset Capability**: Button-triggered system reset with LED indication
- **UDP Communication**: Reliable network communication between devices
- **Color-coded Visualization**: Different colors for different swarm devices

## System Architecture

### Hardware Components

#### ESP8266 Devices
- **Light Sensor**: Photoresistor (A0 pin)
- **RGB LED**: Visual feedback (D4 pin)
- **On-board LED**: Master status indication (GPIO 16)
- **Network**: WiFi connectivity for UDP communication

#### Raspberry Pi 5
- **Button**: System reset trigger (GPIO 22)
- **Yellow LED**: Reset indication (GPIO 26)
- **Network**: WiFi connectivity for UDP communication
- **Display**: Real-time data visualization

### Software Components

#### ESP8266 Code (`ESP_code/ESP_code.ino`)
- WiFi connection management
- Light sensor reading and processing
- UDP communication with other devices
- Master/slave logic implementation
- LED control based on status

#### Raspberry Pi Code (`main.py`)
- UDP message reception and processing
- Real-time data visualization using matplotlib
- Button monitoring and system reset
- Data logging and file management
- GPIO control for LEDs and button

## Installation and Setup

### Prerequisites

#### For ESP8266 Devices
- Arduino IDE with ESP8266 board support
- Required libraries:
  - ESP8266WiFi
  - WiFiUdp

#### For Raspberry Pi 5
- Python 3.7+
- Required Python packages:
  ```bash
  pip install gpiod matplotlib
  ```

### Hardware Setup

#### ESP8266 Setup
1. Connect photoresistor to A0 pin
2. Connect RGB LED to D4 pin
3. Ensure stable power supply
4. Connect to WiFi network

#### Raspberry Pi 5 Setup
1. Connect button to GPIO 22 (with pull-down resistor)
2. Connect yellow LED to GPIO 26 (with current-limiting resistor)
3. Ensure stable power supply
4. Connect to same WiFi network as ESP devices

### Software Configuration

#### ESP8266 Configuration
1. Update WiFi credentials in `ESP_code.ino`:
   ```cpp
   const char* ssid = "your_network_name";
   const char* password = "your_network_password";
   ```

2. Verify UDP port settings:
   ```cpp
   const unsigned int localPort = 4210;
   ```

3. Upload code to ESP8266 devices

#### Raspberry Pi Configuration
1. Ensure GPIO permissions:
   ```bash
   sudo usermod -a -G gpio $USER
   ```

2. Verify GPIO chip configuration in `main.py`:
   ```python
   chip = gpiod.Chip('gpiochip4')  # Adjust if needed
   ```

3. Run the main application:
   ```bash
   python3 main.py
   ```

## System Operation

### Communication Protocol

#### ESP-to-ESP Messages
- **Format**: `~~~swarmID,reading---`
- **Purpose**: Broadcast light readings to other devices
- **Frequency**: Every 100ms if no message received

#### ESP-to-RPi Messages
- **Format**: `+++swarmID,reading***`
- **Purpose**: Master device reports status to Raspberry Pi
- **Frequency**: Only when device is master

#### RPi-to-ESP Messages
- **Format**: `+++RESET_REQUESTED***`
- **Purpose**: System reset command
- **Trigger**: Button press on Raspberry Pi

### Master Selection Logic

1. Each ESP8266 reads light intensity from photoresistor
2. Device broadcasts its reading to all other devices
3. Device compares its reading with received readings
4. Device with highest reading becomes master
5. Master device communicates status to Raspberry Pi
6. Process repeats every 100ms

### Data Visualization

The Raspberry Pi provides two real-time graphs:

1. **Line Graph**: Shows light readings over the last 30 seconds
   - X-axis: Time (seconds ago)
   - Y-axis: Analog reading (0-1023)
   - Color: Changes based on current master device

2. **Bar Graph**: Shows total master duration for each device
   - X-axis: Swarm ID
   - Y-axis: Duration (seconds)
   - Color: Unique color for each swarm device

### Logging System

#### Automatic Logging
- All received data is automatically logged with timestamps
- Logs include swarm ID, light readings, and IP addresses
- Log files are created with timestamps: `master_log_YYYY-MM-DD_HH-MM-SS.txt`

#### Manual Log Management
- Press button on Raspberry Pi to save current logs
- Button press creates new log file and resets system
- Yellow LED indicates reset process (3 seconds)

## Usage Instructions

### Starting the System

1. **Power on all ESP8266 devices**
   - Ensure they connect to WiFi
   - Verify serial output shows assigned swarm IDs

2. **Start Raspberry Pi application**
   ```bash
   python3 main.py
   ```

3. **Monitor system operation**
   - Watch real-time graphs
   - Check serial output for device status
   - Verify LED indicators

### System Reset

1. **Press button on Raspberry Pi**
   - Yellow LED will light for 3 seconds
   - All devices will reset to initial state
   - New log file will be created

2. **Automatic reset behavior**
   - All ESP devices return to master state
   - Competition resumes immediately
   - Previous logs are preserved