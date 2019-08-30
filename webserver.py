from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random, time, threading

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def load_template():
    return render_template('index.html')

@socketio.on('connects_data')
def handle_message(message):
    print("received message: " +message)


def send_temperature():
    while threading.main_thread().isAlive():
        x = random.randrange(11)
        print(str(x))
        socketio.emit('send_temperature', {'data': x})
        socketio.sleep(10);
        
        

if __name__ == '__main__':
    socketio.start_background_task(send_temperature)
    socketio.run(app)
