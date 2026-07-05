import torch
import torchvision
from torchvision import models, transforms
import json
import cv2
from PIL import Image
import numpy as np
from datetime import datetime
import RPi.GPIO as GPIO
import serial
import time,sys     
import os

GPIO.setwarnings(False)

# Set the GPIO mode (BCM or BOARD)
GPIO.setmode(GPIO.BOARD)

# Enable Serial Communication
SERIAL_PORT = "/dev/ttyS0"
ser = serial.Serial(SERIAL_PORT, baudrate = 9600, timeout = 5)

prevTime = 0

# Define the GPIO pin number to which the buzzer is connected
BUZZER_PIN = 37

# Set up the GPIO pin as an output
GPIO.setup(BUZZER_PIN, GPIO.OUT)
# Set the GPIO pin to LOW
GPIO.output(BUZZER_PIN, GPIO.LOW)

location = 'Nashik'

log_file = 'logs.jsonl'

def save_log(animal, location, current_time):
    log_entry = {
        'detected_animal': animal,
        'location': location,
        'detection_time': current_time
        }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + "\n")
    
def sendMessage(label):
    cdatetime = datetime.now()
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    ser.write(str.encode('AT+CMGF=1\r'))
    print("Text mode enabled...")
    time.sleep(3)
    ser.write(str.encode('AT+CMGS="0123456789"\r')) #your mobile number
    msg=f"Be Alert, {label} Detected near {location} at {cdatetime}."
    print("sending message....")
    time.sleep(3)
    ser.write(str.encode(msg+chr(26)))
    time.sleep(3)
    print("message sent...")
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    

#sendMessage()         

model= models.resnet18(pretrained= True)
model.eval()
transform= transforms.Compose([transforms.Resize((224,224)),
                               transforms.ToTensor(),
                               transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
with open("./imagenet_class_index.json", "r") as f:
    class_names = json.load(f)
    
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    res, frame = cap.read()
    if not res:
        print("Error: Failed to capture frame.")
        break
    
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    img = transform(img).unsqueeze(0)

    with torch.no_grad():
        output = model(img)

    _, prediction = torch.max(output, 1)
    label_index = prediction.item()
    label = class_names[str(label_index)][2]
    label1 = class_names[str(label_index)][1]
    
    if label=="Animal":
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        command = f"espeak -s {120} '{label1} is detected at {location}'"
        os.system(command)
        print("Animal - ")
        print(label1)
        t = time.localtime()
        current_time = time.strftime("%H", t)
        ctime = datetime.utcnow().isoformat()
        print(current_time)
        print(prevTime)
        print(int(current_time)!=prevTime)
        save_log(label1, location, ctime)
        if (int(current_time)!=prevTime):
            sendMessage(label1)
            prevTime = int(current_time)
        else:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            print("Message already sent for this hour")
            time.sleep(2)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        
        

    cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

   
    cv2.imshow("Animal Detection", frame)
 
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
