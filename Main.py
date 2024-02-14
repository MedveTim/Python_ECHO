from time import sleep
import threading
from threading import Thread
import serial
import matplotlib.pyplot as plt
import numpy as np
from pynput import keyboard


def print_pressed_keys(e):
    global flag
    flag = False

def print_chart(data_packet):
    plt.clf()
    plt.plot(np.array(data_packet))        
    plt.draw()
    plt.title('А-развёртка')
    plt.xlabel('Время, мс')
    plt.ylabel('Амплитуда')
    plt.grid(True)
    plt.gcf().canvas.flush_events()


def send_settings():
    packet = bytearray([36, 2, 8, 0, 0, 9, 1, 146, 3, 0, 0, 100])
    global ser
    while flag == True:
        ser.write(packet)
        #print('Отправил настройки')
        sleep(2)


def get_packet():
    global data_packet
    global data_packet_for_test_chart
    while flag == True:
        data = ser.read(601) #понять что тут
        if len(data) > 0:
            with locker:
                data_packet += data # всё что есть просто добывляем в массив
                #print(f'Длина data_packet = {len(data_packet)}')
                #print(data)
            sleep(0.05)

def Find_marker(data_packet, x=0):
    flag = 0
    while x + 3 <= len(data_packet):
        if data_packet[x] == 0xff and data_packet[x + 1] == 0xff and data_packet[x + 2] == 0x00 and data_packet[x + 3] == 0x00:
            flag = 1
            break
        x += 1
    if flag == 0:
        return -1
    return x


def from_bytes_to_numbers(data_packet_good_local):
    data_packet_good_local = data_packet_good_local[16:]
    i = 0
    data_packet_good_num = []
    while i + 2 <= len(data_packet_good_local) - 1: # "-1" так как смотрим по индексам
        a = ((0x0000 + (data_packet_good_local[i + 2] & 0x0f)) << 8) + data_packet_good_local[i]
        data_packet_good_num.append(a)
        b = ((0x0000 + (data_packet_good_local[i + 2] & 0xf0)) << 4) + data_packet_good_local[i + 1]
        data_packet_good_num.append(b)
        i += 3
    return data_packet_good_num


locker = threading.Lock()
flag = True
data_packet = bytearray()

port = "COM5" # настройка СОМ-порта
baudrate = 115200
ser = serial.Serial(port, baudrate=baudrate, bytesize=8)

thread_get_packet = Thread(target=get_packet) # создаём потоки
thread_send_settings = Thread(target=send_settings)

thread_get_packet.start() # открываем потоки
thread_send_settings.start()

a = keyboard.Listener(on_release=print_pressed_keys) # смотрим на нажатия клавиш
a.start()

plt.ion()

data_packet_good = bytearray()

while flag == True:
    sleep(0.1)
    with locker:
        if len(data_packet_good) > 0: # если в хорошем массиве есть только часть пачки, то ишем конец, добавляем к тому что уже есть и рисуем
            j = Find_marker(data_packet)
            
            if j == -1: # если нет конца просто запоминаем то что уже есть
                data_packet_good += data_packet
                data_packet = bytearray()
                
                #print("нет конца пачки4")
            else: # если нашли конец рисуем график
                data_packet_good += data_packet[:j]
                #print(f'!!!Длина пачки = {len(data_packet_good)} внутри >> {data_packet_good}')
                print_chart(from_bytes_to_numbers(data_packet_good)) # переводим байты в числа и рисуем график
                data_packet_good = bytearray()
                data_packet = bytearray()                

        else: # ищем начало и конец пачки и записываем в хороший массив, который будем печатать
            i = Find_marker(data_packet)
            
            if i == -1: # если не нашли начало
                data_packet = bytearray()
            else: # если нашли начало
                j = Find_marker(data_packet, i + 4)
                
                if j == -1: # если не нашни конец запоминаем то что есть
                    data_packet_good += data_packet[i:]
                    data_packet = bytearray()
                    
                    #print("нет конца пачки")
                else: # если нашли и начало и конец то рисуем график
                    data_packet_good = data_packet[i:j]
                    #print(f'!!!Длина пачки = {len(data_packet_good)} внутри >> {data_packet_good}')
                    print_chart(from_bytes_to_numbers(data_packet_good)) # переводим байты в числа и рисуем график
                    data_packet_good = bytearray()
                    data_packet = bytearray()

thread_get_packet.join() # дожидаемся окончания работы потоков
thread_send_settings.join()

a.stop() # закрываем СОМ-порт
ser.close()