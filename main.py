import gpiod
import time
import socket
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque, defaultdict
from datetime import datetime

# Constants for GPIO pins and communication protocol
BUTTON_PIN = 22  # GPIO pin for the button
YELLOW_LED_PIN = 26  # GPIO pin for yellow LED
RPi_startBit = "+++"  # Start delimiter for messages
RPi_endBit = "***"  # End delimiter for messages
localPort = 4210  # Port to listen for incoming UDP messages

# Initialize GPIO chip and request lines for button and LEDs
chip = gpiod.Chip('gpiochip4')
button_line = chip.get_line(BUTTON_PIN)
button_line.request(consumer="Button", type=gpiod.LINE_REQ_DIR_IN)
yellow_led_line = chip.get_line(YELLOW_LED_PIN)
yellow_led_line.request(consumer="Yellow_LED", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])

# Set up UDP socket for communication and enable broadcast mode
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', localPort))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

print(f"Listening for incoming messages on port {localPort}...")

# Global variables
PREV_BUTTON_STATE = 0
RESET_REQUEST = False  # Tracks if a reset request is active
STOP_THREADS = False
ANALOG_READINGS = deque(maxlen=30)  # Store up to 30 readings (one per second)
SWARM_COLORS = {}  # To store assigned colors for each Swarm ID
CURRENT_MASTER = None  # To track the current master Swarm ID
MASTER_DURATION_TRACK = defaultdict(int)  # To track how long each Swarm ID has been master
MASTER_LOG_TRACK = defaultdict(list)  # Raw data logs for each master
LOG_FILE = None
start_time = datetime.now()

def get_new_log_file():
    """Creates a new log file with the current timestamp."""
    # Inputs: None
    # Process: Generate a timestamp and create a log file name
    # Output: Updates the global LOG_FILE variable with the new log file name and prints the name
    global LOG_FILE
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    LOG_FILE = f"master_log_{timestamp}.txt"
    print(f"New log file created: {LOG_FILE}")

def save_current_logs():
    """Save the logs to the current log file."""
    # Inputs: None
    # Process: Writes the current log information (masters summary, raw logs) to the LOG_FILE
    # Output: Saves the log data to a file and prints the save confirmation
    global LOG_FILE, MASTER_DURATION_TRACK, MASTER_LOG_TRACK
    if not LOG_FILE:
        return
    
    with open(LOG_FILE, 'w') as log_file:
        log_file.write(f"Log File Created: {datetime.now()}\n\n")
        log_file.write("Masters Summary:\n")
        for swarm_id, duration in MASTER_DURATION_TRACK.items():
            log_file.write(f"Swarm ID: {swarm_id}, Total Master Duration: {duration} seconds\n")
        
        log_file.write("\nRaw Data Logs:\n")
        for ip, logs in MASTER_LOG_TRACK.items():
            log_file.write(f"\nIP: {ip}\n")
            log_file.write('\n'.join(logs) + '\n')
    
    print(f"Logs saved to {LOG_FILE}")

def reset_system():
    """Function to handle reset message."""
    # Inputs: None
    # Process: Resets global variables, broadcasts a reset message, and signals a reset with the yellow LED
    # Output: Updates relevant variables, sends a broadcast, and controls the yellow LED
    global RESET_REQUEST, SWARM_COLORS, CURRENT_MASTER, MASTER_DURATION_TRACK, LOG_FILE, ANALOG_READINGS
    
    RESET_REQUEST = True  # Prevents other actions during reset

    # Broadcast reset request message to all devices
    reset_message = f"{RPi_startBit}RESET_REQUESTED{RPi_endBit}"
    print(f"Button is pressed. Broadcast: {reset_message}")
    sock.sendto(reset_message.encode('utf-8'), ('<broadcast>', localPort))

    # Reset swarm colors, master tracking, durations, and analog readings
    SWARM_COLORS = {}
    CURRENT_MASTER = None
    MASTER_DURATION_TRACK.clear()
    ANALOG_READINGS.clear()

    # Light up yellow LED for 3 seconds to indicate reset
    yellow_led_line.set_value(1)
    time.sleep(3)
    yellow_led_line.set_value(0)
    
    RESET_REQUEST = False

def listen_for_messages():
    """Function to listen for UDP messages, process sensor data, and control the LED."""
    # Inputs: None
    # Process: Listens for UDP messages, processes them, updates relevant global variables
    # Output: Updates global state based on received data (analog readings, swarm ID, etc.)
    global RESET_REQUEST, STOP_THREADS, CURRENT_MASTER, LOG_FILE

    while not STOP_THREADS:
        if not RESET_REQUEST:  # Skip listening if reset is active
            try:
                message, address = sock.recvfrom(1024)
            except socket.error:
                break  # Break if socket is closed

            message = message.decode('utf-8')

            # Check for message start and end delimiters
            if message.startswith(RPi_startBit) and message.endswith(RPi_endBit):
                data = message[len(RPi_startBit):-len(RPi_endBit)]
                ip = address[0]

                if ',' in data:
                    swarm_id, analog_reading = data.split(',')  
                else:
                    continue

                log_entry = f"Time: {datetime.now()}, Swarm ID: {swarm_id}, Reading: {analog_reading}"
                MASTER_LOG_TRACK[ip].append(log_entry)
                print(f"Received from {ip}: {log_entry}")
                
                # Skip processing if message is reset request confirmation
                if data == "RESET_REQUESTED":
                    continue
                
                # Extract Swarm ID and analog reading from message
                swarm_id, analog_reading = data.split(',')
                # Update the ANALOG_READINGS deque with the new reading
                ANALOG_READINGS.append(int(analog_reading))

                # Assign color to Swarm ID if it's not already assigned
                if swarm_id not in SWARM_COLORS:
                    if len(SWARM_COLORS) == 0:
                        SWARM_COLORS[swarm_id] = 'red'
                    elif len(SWARM_COLORS) == 1:
                        SWARM_COLORS[swarm_id] = 'green'
                    else:
                        SWARM_COLORS[swarm_id] = 'yellow'

                if CURRENT_MASTER != swarm_id:
                    CURRENT_MASTER = swarm_id
                    print(f"New master detected: {swarm_id}")

                MASTER_DURATION_TRACK[swarm_id] += 1

def monitor_button():
    """Monitor the button state and handle resets and log rotation on press."""
    # Inputs: None
    # Process: Detects button presses, saves logs, resets the system on press
    # Output: Triggers log saving, file creation, and system reset when the button is pressed
    global PREV_BUTTON_STATE, STOP_THREADS

    while not STOP_THREADS:
        button_state = button_line.get_value()
        if button_state == 1 and PREV_BUTTON_STATE == 0:  # Button press detected
            save_current_logs()  # Save existing logs
            get_new_log_file()  # Start a new log file
            reset_system()  # Call reset if button is pressed

        PREV_BUTTON_STATE = button_state
        time.sleep(0.1)

def plot_graph():
    # Inputs: None
    # Process: Plots real-time data (analog readings and master durations) in a graph using Matplotlib
    # Output: Displays real-time updated graph with master durations and analog readings
    global RESET_REQUEST, STOP_THREADS, ANALOG_READINGS, CURRENT_MASTER, SWARM_COLORS, MASTER_DURATION_TRACK

    # Variables for graphing
    x_data = list(range(30))  # X-axis for line graph
    y_data = [0] * 30  # Initial Y-axis data
    bar_data = defaultdict(int)  # Bar data for master durations

    while not STOP_THREADS:
        # Initialize the figure and subplots
        fig, (ax1, ax2) = plt.subplots(2, 1)
        fig.subplots_adjust(hspace=0.5)

        # Configure line graph (real-time readings)
        ax1.set_ylim(0, 1023)
        ax1.set_xlim(0, 29)
        ax1.set_xlabel('Time (seconds ago)')
        ax1.set_ylabel('Analog Reading')
        ax1.set_title('Real-time Analog Readings (last 30 seconds)')
        line, = ax1.plot(x_data, y_data, color='blue', lw=2)

        # Configure bar graph (master durations)
        ax2.set_ylim(0, 30)
        ax2.set_xlabel('Swarm ID')
        ax2.set_ylabel('Duration (seconds)')
        ax2.set_title('Master Device Durations (total time)')

        def update_plot(frame):
            nonlocal line, y_data

            # Update the line graph data
            if ANALOG_READINGS:
                y_data = list(ANALOG_READINGS) + [0] * (30 - len(ANALOG_READINGS))
            else:
                y_data = [0] * 30

            # Update line color based on current master
            if CURRENT_MASTER:
                color = SWARM_COLORS.get(CURRENT_MASTER, 'blue')
                line.set_color(color)

                # Update master duration
                bar_data[CURRENT_MASTER] += 1

            line.set_ydata(y_data)
            return line,

        def update_bar(frame):
            ax2.clear()
            ax2.bar(MASTER_DURATION_TRACK.keys(), MASTER_DURATION_TRACK.values(), 
                    color=[SWARM_COLORS.get(sid, 'blue') for sid in MASTER_DURATION_TRACK.keys()])
            ax2.set_ylim(0, max(MASTER_DURATION_TRACK.values(), default=30))
            ax2.set_xlabel('Swarm ID')
            ax2.set_ylabel('Duration (seconds)')
            ax2.set_title('Master Device Durations (total time)')

        # Setup animations
        ani1 = FuncAnimation(fig, update_plot, interval=1000)
        ani2 = FuncAnimation(fig, update_bar, interval=1000)

        # Display the plot
        plt.show()

        # Check for reset
        while RESET_REQUEST:
            plt.close(fig)  # Close the current figure
            x_data = list(range(30))  # Reset X data
            y_data = [0] * 30  # Reset Y data
            bar_data.clear()  # Reset bar data
            MASTER_DURATION_TRACK.clear()  # Reset master durations
            break  # Exit the inner loop to reinitialize the graph


# Main entry point to start button monitoring, message listening, and graph display
if __name__ == "__main__":
    try:
        get_new_log_file()  # Initialize the first log file

        # Create separate threads for button monitoring, message reception, and plotting
        button_thread = threading.Thread(target=monitor_button)
        receive_thread = threading.Thread(target=listen_for_messages)
        graph_thread = threading.Thread(target=plot_graph)

        # Start the threads
        button_thread.start()
        receive_thread.start()
        graph_thread.start()

        # Keep the program running by joining the threads
        button_thread.join()
        receive_thread.join()
        graph_thread.join()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Shutting down...")
        STOP_THREADS = True  # Signal threads to stop
        sock.close()  # Close the socket
        button_thread.join()  # Ensure the threads are properly stopped
        receive_thread.join()
        print("Shutdown complete.")
