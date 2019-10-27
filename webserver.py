from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random, time, threading, mySI7021
import board, busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import logging

#Stops flask server status clogging up stdout
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#TEMP SENSOR SETUP
th_sensor = mySI7021.temp_humid()

#SOIL SENSOR SETUP
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1015(i2c)
chan = AnalogIn(ads, ADS.P0)

#GLOBAL VARIABLES
soilmoisture_setpoint = 50
temperature_setpoint = 23
vent_open = None
vent_closed = None

#THREADING EVENTS
start_vent_event = threading.Event()
open_vent_event = threading.Event()
close_vent_event = threading.Event()
end_vent_event = threading.Event()
start_watering_event = threading.Event()
add_water_event = threading.Event()

#FLASK AND SOCKET IO SETUP
app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def load_template():
    return render_template('index.html')

@socketio.on('connects_data')
def handle_message(message):
    print("received message: " +message)
    if vent_open is True:
        socketio.emit('send_vent_position',{'pos' : "Open"})
    elif vent_closed is True:
        socketio.emit('send_vent_position',{'pos' : "Closed"})


#This will be my main control loop that will read sensor information.
#It will spawn other threads where needed for actions with faster update time.
def send_temperature():
    
    
    while threading.main_thread().is_alive(): #Shuts this thread down when main thread is Ctrl-C'd after its completed.
        
        """
        READING TEMPERATURE AND HUMIDITY FROM SI7021
        """
        th_sensor.humidity_temp_set()
        h = th_sensor.humidity_get()
        t = th_sensor.temp_get()
        print("temp: {}, humid: {}".format(t, h))
        socketio.emit('send_temperature', {'temp': t,
                                           'humid': h,
                                           'temp_setpoint': temperature_setpoint
                                           })

        """
        READING SOIL MOISTURE SENSOR
        """
        soilmoistureADC = chan.value
        #Map ADC value to 0...100%
        soilmoistureMAP = (((soilmoistureADC - 0) * (100 - 0)) / (30000 - 0))+0
        #String format to 2 decimal places
        soilmoistureMAP_string = "{:.2f}".format(soilmoistureMAP)
        print("soil sensor value: " + str(soilmoistureMAP))
        socketio.emit('send_soilmoisture', {'JSsoil' : soilmoistureMAP_string})
        if soilmoistureMAP < 40 and start_watering_event.is_set() is False:
            start_watering_event.set()
            add_water_event.set()
            print("Started watering thread")
        elif soilmoistureMAP >= 40:
            socketio.emit('watering_info', {'watering_status' : "Well Hydrated"})


        """
        LOGIC TO OPEN OR CLOSE VENTS DEPENDING ON TEMPERATURE.
        SETS EVENTS IN 'OPEN_CLOSE_VENTS()' THREAD
        """
        if t > temperature_setpoint and not vent_open:
            start_vent_event.set()
            open_vent_event.set()
        if t < temperature_setpoint and not vent_closed:
            start_vent_event.set()
            close_vent_event.set()
            
        socketio.sleep(10);
    
    """
    IF MAIN THREAD EXITS, SHUTS DOWN THREADS GRACEFULLY.
    """
    if threading.main_thread().is_alive() == False:
        #Kill off vent control thread gracefully
        open_vent_event.clear()
        close_vent_event.clear()
        start_vent_event.set()
        #Kill off watering thread gracefully
        add_water_event.clear()
        start_watering_event.set()


#OPEN AND CLOSE VENT THREAD
def open_close_vents():
    global vent_closed
    global vent_open


    while start_vent_event.wait():
        
        if open_vent_event.is_set():
            print("I am opening the vents")
            socketio.emit('send_vent_position',{'pos' : "Going Open"})
            vent_closed = False
            socketio.sleep(3)
            vent_open = True
            socketio.emit('send_vent_position',{'pos' : "Open"})
            print("I have opened the vents")
            open_vent_event.clear()
        
        if close_vent_event.is_set():
            print("I am closing the vents")
            socketio.emit('send_vent_position',{'pos' : "Going Closed"})
            vent_open = False
            socketio.sleep(3)
            vent_closed = True
            socketio.emit('send_vent_position',{'pos' : "Closed"})
            print("I have closed the vents")
            close_vent_event.clear()
            
        if threading.main_thread().is_alive() == True:
            start_vent_event.clear()
        else:
            break

#WATERING THREAD
def watering_thread():
    watering_count = 1
    while start_watering_event.wait():
        if add_water_event.is_set():
            print("I am watering")
            socketio.emit('watering_info', {'watering_status' : "Watering Plants"})
            socketio.sleep(5)
            socketio.emit('watering_info', {'watering_status' : "Finished Watering"})
            print("I am taking a sleep")
            socketio.sleep(5)
            add_water_event.clear()


        if threading.main_thread().is_alive() == True:
            start_watering_event.clear()
        else:
            break


if __name__ == '__main__':
    socketio.start_background_task(send_temperature)
    socketio.start_background_task(open_close_vents)
    socketio.start_background_task(watering_thread)
    socketio.run(app, host="0.0.0.0")
    
