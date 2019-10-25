from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random, time, threading, mySI7021
import board, busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

th_sensor = mySI7021.temp_humid()

#SOIL SENSOR SETUP
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1015(i2c)
chan = AnalogIn(ads, ADS.P0)

vent_open = None
vent_closed = None


start_vent_event = threading.Event()
open_vent_event = threading.Event()
close_vent_event = threading.Event()
end_vent_event = threading.Event()

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def load_template():
    return render_template('index.html')

@socketio.on('connects_data')
def handle_message(message):
    print("received message: " +message)
    


#This will be my main control loop that will read sensor information.
#It will spawn other threads where needed for actions with faster update time.
def send_temperature():
    
    
    while threading.main_thread().is_alive(): #Shuts this thread down when main thread is Ctrl-C'd after its completed.
        
        """
        reading temperature and humidity from SI7021
        """
        th_sensor.humidity_temp_set()
        h = th_sensor.humidity_get()
        t = th_sensor.temp_get()
        print("temp: {}, humid: {}".format(t, h))
        socketio.emit('send_temperature', {'temp': t,
                                           'humid': h})

        #soil sensor read
        print("soil sensor value: " + str(chan.value))

        """
        logic to open or close vents depending on temperature.
        sets events in 'open_close_vents()' thread
        """
        print(vent_closed)
        if t > 22 and not vent_open: #close_vent_event.is_set() == False and open_vent_event.is_set() == False: #and open_vent_event.is_set() == False:
            start_vent_event.set()
            open_vent_event.set()
        if t < 21.5 and not vent_closed: #open_vent_event.is_set() == False and close_vent_event.is_set() == False:
            start_vent_event.set()
            close_vent_event.set()
            
        #print(start_vent_event.is_set(), close_vent_event.is_set())
        socketio.sleep(10);
    
    """
    if main thread exits, shuts down 'open_close_vents()' thread gracefully.
    """
    if threading.main_thread().is_alive() == False:
        open_vent_event.clear()
        close_vent_event.clear()
        start_vent_event.set()

        


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


    

if __name__ == '__main__':
    socketio.start_background_task(send_temperature)
    socketio.start_background_task(open_close_vents)
    socketio.run(app, host="0.0.0.0")
    
