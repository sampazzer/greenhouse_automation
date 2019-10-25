#---SI7021 CLASS---#

from smbus2 import SMBus, i2c_msg
import time


class temp_humid:
    """My class to handle the readings from the SI7021 temp humid sensor
    """
    def __init__(self):
        self.address = 0x40
        self.humidityCommand = 0xF5
        self.tempCommand = 0xE0
        self.temp_value = None
        self.humidity_value = None

    def humidity_temp_set(self):
        """Sends command to read humidity. Then reads humidity with a pause between the two bytes.
        Temperature then reads as a temp reading is taken by the sensor for compensation for humidity reading
        """
        #---HUMIDITY I2C WRITE READ---#
        with SMBus(1) as bus:
            self.humidity_write = i2c_msg.write(self.address,[self.humidityCommand])
            self.humidity_read = i2c_msg.read(self.address,2)
            bus.i2c_rdwr(self.humidity_write)
            time.sleep(0.35)
            bus.i2c_rdwr(self.humidity_read)

        #---TEMP I2C WRITE READ---#
        with SMBus(1) as bus:
            self.temp_write = i2c_msg.write(self.address,[self.tempCommand])
            self.temp_read = i2c_msg.read(self.address,2)
            bus.i2c_rdwr(self.temp_write)
            bus.i2c_rdwr(self.temp_read)

    def humidity_get(self):
        """Carries out the maths for the humidity reading and returns it in %
        """
        #---HUMIDITY VALUE EDITING---#
        humidity_byte_list = list(self.humidity_read)
        humidity_MSB = humidity_byte_list[0]
        humidity_LSB = humidity_byte_list[1]
        humidity_word = (humidity_MSB<<8) + humidity_LSB
        self.humidity_value = ((125.0*humidity_word)/65536.0) - 6
        return round(self.humidity_value,2)

    def temp_get(self):
        """Carries out the maths for the temperature reading and returns it in DegC
        """
        #---TEMPERATURE VALUE EDITIING---#
        temp_byte_list = list(self.temp_read)
        temp_MSB = temp_byte_list[0]
        temp_LSB = temp_byte_list[1]
        temp_word = (temp_MSB<<8) + temp_LSB
        self.temp_value = ((175.72*temp_word)/65536)-46.85
        return round(self.temp_value,2)
