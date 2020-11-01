
# -*- coding: utf-8 -*-


import Adafruit_DHT
from Adafruit_BMP085 import BMP085
import RPi.GPIO as GPIO
import time
import pytz
from datetime import datetime
import threading
import uuid
import math 
import requests

bmp = BMP085(0x77)
DHT_SENSOR = Adafruit_DHT.DHT11
GPIO.setmode(GPIO.BCM)
DHT_PIN = 4
TRIG = 23
ECHO = 24

temp_array = []
humidity_array = []
pressure_array = []
rainfall_array = []


# This function converts parameters into an XML message using Common Alerting Protocol       
def capFormat(current_datetime, temperature_mean, temperature_sd, humidity_mean, humidity_sd, pressure_mean, pressure_sd, rainfall_mean, rainfall_sd):   
    
    return """<alert xmlns = 'urn:oasis:names:tc:emergency:cap:1.2'>

                  <identifier>"""+str(uuid.uuid4())+"""</identifier> 

                  <sender>170494F_yoshani.ranaweera.17@cse.mrt.ac.lk</sender> 

                  <sent>"""+current_datetime+"""</sent>

                  <status>Actual</status> 

                  <msgType>Alert</msgType>

                  <scope>Public</scope>

                  <info>

                    <category>Geo</category>

                    <event>Environmental monitoring</event>   

                    <urgency>Immediate</urgency>   

                    <severity>Minor</severity>   

                    <certainty>Observed</certainty>

                    <headline>Environmental monitoring parameters</headline>

                    <parameter>

                      <valueName>Date</valueName>

                      <value>"""+current_datetime+"""</value>

                    </parameter>

                    <parameter>

                      <valueName>TemperatureMean</valueName>

                      <value>"""+temperature_mean+"""</value>

                    </parameter>

                    <parameter>

                      <valueName>TemperatureSD</valueName>

                      <value>"""+temperature_sd+"""</value>

                    </parameter>

                    <parameter>

                      <valueName>HumidityMean</valueName>

                      <value>"""+humidity_mean+"""</value>

                    </parameter>

                    <parameter>

                      <valueName>HumiditySD</valueName>

                      <value>"""+humidity_sd+"""</value>

                    </parameter>
                    
                    <parameter>

                      <valueName>PressureMean</valueName>

                      <value>"""+pressure_mean+"""</value>

                    </parameter>

                    <parameter>

                      <valueName>PressureSD</valueName>

                      <value>"""+pressure_sd+"""</value>

                    </parameter>
                    
                    <parameter>

                      <valueName>RainfallMean</valueName>

                      <value>"""+rainfall_mean+"""</value>

                    </parameter>

                    <parameter>

                      <valueName>RainfallSD</valueName>

                      <value>"""+rainfall_sd+"""</value>

                    </parameter>

                  </info>

                </alert>"""



# This function finds mean and standard deviation of measurements
def findAverages(run_event):

    global temp_array
    global humidity_array
    global pressure_array
    global rainfall_array 
    
    while run_event.is_set():
        
        time.sleep(900)  # measure in 15 minute intervals
        
        temp_length = len(temp_array)
        humidity_length = len(humidity_array)
        pressure_length = len(pressure_array)
        rainfall_length = len(rainfall_array)
        
        total_temp = 0
        squared_total_temp = 0
        total_humidity = 0
        squared_total_humidity = 0
        total_pressure = 0
        squared_total_pressure = 0
        total_rainfall = 0
        squared_total_rainfall = 0
        
        if temp_length and humidity_length and pressure_length != 0:
            for i in range(temp_length):
                total_temp+=temp_array[i]
                squared_total_temp+=((temp_array[i])**2)
            for i in range(humidity_length):
                total_humidity+=humidity_array[i]
                squared_total_humidity+=((humidity_array[i])**2)
            for i in range(pressure_length):
                total_pressure+=pressure_array[i]
                squared_total_pressure+=((pressure_array[i])**2)
            for i in range(rainfall_length):
                total_rainfall+=rainfall_array[i]
                squared_total_rainfall+=((rainfall_array[i])**2)
            
            #find mean
            t_mean = float(total_temp)/temp_length
            temperature_mean = '{0:0.1f}C'.format(t_mean) 
            h_mean = float(total_humidity)/humidity_length
            humidity_mean = '{0:0.1f}%'.format(h_mean)
            p_mean = float(total_pressure)/pressure_length
            pressure_mean = '{0:0.2f} Pa'.format(p_mean)
            r_mean = float(total_rainfall)/rainfall_length
            rainfall_mean = str(round(r_mean, 3))+' mm'
            
            #find standard deviation
            temperature_sd = '{0:0.1f}C'.format(math.sqrt((float(squared_total_temp)/temp_length)-(t_mean**2)))
            humidity_sd = '{0:0.1f}%'.format(math.sqrt((float(squared_total_humidity)/humidity_length)-(h_mean**2)))
            pressure_sd = '{0:0.2f} Pa'.format(math.sqrt((float(squared_total_pressure)/pressure_length)-(p_mean**2)))
            rainfall_sd = str(round(math.sqrt((float(squared_total_rainfall)/rainfall_length)-(r_mean**2)),3))+' mm'
             
            print("Calculated mean values:")
            print(temperature_mean, humidity_mean, pressure_mean, rainfall_mean)
            print("Calculated sd values:")
            print(temperature_sd, humidity_sd, pressure_sd, rainfall_sd)
            
            #local time in CAP valid format
            tz = pytz.timezone('Asia/Colombo')
            dt = datetime.now()
            loc_dt = tz.localize(dt).replace(microsecond=0)
            current_datetime = str(loc_dt.isoformat())
            
            temp_array = []
            humidity_array = []
            pressure_array = []
            rainfall_array = []

            cap_alert = capFormat(current_datetime, temperature_mean, temperature_sd, humidity_mean, humidity_sd, pressure_mean, pressure_sd, rainfall_mean, rainfall_sd)
            
            f = open("cache.txt", "a")
            f.write(cap_alert.replace("\n", '') + "\n")     #save CAP alerts in cache file 
            f.close()
   
   
# This function measures and returns rainfall 
def measureDistance():
    gauge_height = 180   #specify height of rain gauge
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    
    while GPIO.input(ECHO)==0:
        pulse_start = time.time()
    while GPIO.input(ECHO)==1:
        pulse_end = time.time()  
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150 * 10
    rainfall_height = gauge_height - distance
    return (rainfall_height)
  

  
# This function measures humidity, temperature, pressure, rainfall
def measureValues(run_event):

    global temp_array
    global humidity_array
    global pressure_array
    global rainfall_array
    
    while run_event.is_set():
        
        humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
        pressure = bmp.readPressure()
        rainfall = measureDistance()
        if humidity is not None and temperature is not None and pressure is not None and rainfall is not None:
            temp_array.append(temperature)
            humidity_array.append(humidity)
            pressure_array.append(pressure)
            rainfall_array.append(rainfall)
            print("Temp={0:0.1f}C Humidity={1:0.1f}%".format(temperature,humidity))
            print ('Pressure = {0:0.2f} Pa'.format(pressure))
            print "Rainfall:",round(rainfall, 3),"mm"
            print ("\n")
        else:
            print("Sensor failure")
        time.sleep(3)



# This function saves data in cache to remote database     
def sendToDatabase(run_event):
    
    url = 'http://54.169.165.139:9191/saveValues'
    
    while run_event.is_set():       
        time.sleep(5)
        cache = []
        try:
            with open("cache.txt", "r") as f:
                cache = f.readlines()
        except IOError:
            print ("waiting for cache to be created")

        if len(cache)!= 0:
            try:
                response = requests.post(url, data=cache[0], headers={'Content-Type':'application/xml; charset=UTF-8'})
                response.raise_for_status()
                cache.pop(0)
                with open("cache.txt", "w") as f:
                    for alert in cache:
                        f.write(alert)
                print ("alert saved in database\n")

            except requests.HTTPError as exception: 
                print("HTTP error")
                
            except requests.ConnectionError:
                print("Network error")
                
            except requests.exceptions.RequestException as e:
                print ("Request error")
                


       
# Main function runs subfunctions as three threads
def main():
    
    run_event = threading.Event()
    run_event.set()
    
    GPIO.setup(TRIG,GPIO.OUT)
    GPIO.setup(ECHO,GPIO.IN)
    GPIO.output(TRIG, False)
    
    time.sleep(5) #time to settle sensors
    
    t1 = threading.Thread(target = measureValues, args = (run_event,))
    t2 = threading.Thread(target = findAverages, args = (run_event,))
    t3 = threading.Thread(target = sendToDatabase, args = (run_event,))

    t2.setDaemon(True)
    
    t1.start()
    t2.start()
    t3.start()

    try:
        while 1:
            time.sleep(.1)
    except KeyboardInterrupt:
        print ("attempting to exit")        
        run_event.clear()
        t1.join()
        t3.join()
        GPIO.cleanup()
        print ("successfully exited")


if __name__ == '__main__':
    main()