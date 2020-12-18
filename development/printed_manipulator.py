'''
Control of 3D printed manipulator made by Jiawei Wang
'''
import serial
import time
from threading import *
import threading


class basic_fonctions:
    course = 10 * 1000 / 2
    a = 0

    def axis(self, axis):
        # axes = ['x','y','z']
        # sens = ['positif','negatif']
        # self.sudu(3)
        # for i in range(1,4):
        if axis == 1:
            self.myservo.write(b'1')
            print('Moving on axis x  direction  str(sens[0])')
            self.Speed = 10. / 90. * self.vitesse_l

        if axis == -1:
            self.myservo.write(b'2')
            print('Moving on axis y direction')
            self.Speed = 10. / 90. * self.vitesse_b * 0.75
        if axis == 2:
            self.myservo.write(b'3')
            print('Moving on axisdirection')
            self.Speed = 10. / 90. * self.vitesse_l * 0.8

        if axis == -2:
            self.myservo.write(b'4')
            print('Moving on axis str(sens[1])')
            self.Speed = 10. / 90. * self.vitesse_l * 1.15

        if axis == 3:
            self.myservo.write(b'5')
            print('Moving on axis str(sens[0])')
            self.Speed = 10. / 90. * self.vitesse_l * 0.8

        if axis == -3:
            self.myservo.write(b'6')
            print('Moving on axis + str(sens[1])')
            self.Speed = 10. / 90. * self.vitesse_l * 1.1
        return (self.Speed)

    def sudu(self, mode):
        # axes = ['x','y','z']
        # sens = ['positif','negatif']
        # self.sudu(3)
        # for i in range(1,4):
        if mode == 1:
            self.myservo.write(b'a')
            print('Moving on axis x  direction  str(sens[0])')
            self.Speed = 10. / 90. * self.vitesse_l

        if mode == 2:
            self.myservo.write(b'b')
            print('Moving on axis y direction')
            self.Speed = 10. / 90. * self.vitesse_l
        if mode == 3:
            self.myservo.write(b'c')
            print('Moving on axisdirection')
            self.Speed = 10. / 90. * self.vitesse_l

        if mode == 4:
            self.myservo.write(b'd')
            print('Moving on axis str(sens[1])')
            self.Speed = 10. / 90. * self.vitesse_l

        if mode == 5:
            self.myservo.write(b'e')
            print('Moving on axis str(sens[0])')
            self.Speed = 10. / 90. * self.vitesse_l

    def runtime(self, axe, distance):

        if axe == 1:
            print(self.Speed)
            self.tx = distance / self.Speed
            print('Working time on axis x :' + str(abs(self.tx)) + 's')
            self.px = self.tx * self.Speed
        elif axe == 2:
            self.ty = distance / self.Speed
            print('Working time on axis y :' + str(abs(self.ty)) + 's')
            self.py = self.ty * self.Speed
        elif axe == 3:
            self.tz = distance / self.Speed
            print('Working time on axis z :' + str(abs(self.tz)) + 's')
            self.pz = self.tz * self.Speed

    def pause(self, axe):
        if axe == 1:
            sleep(abs(self.tx))
        elif axe == 2:
            sleep(abs(self.ty))
        elif axe == 3:
            sleep(abs(self.tz))

    def Pas(self, taille_pas):
        self.pas = 0.05 * taille_pas
        return self.pas

    def steptime(self, axis, distance, taille_pas, mode):
        self.sudu(mode)
        if axis == 1:
            self.px = self.tx * self.Speed
            self.nbp = int(distance / (self.pas * self.Speed))
        elif axis == 2:
            self.py = self.ty * self.Speed
            self.nbp = int(distance / (self.pas * self.Speed))
        elif axis == 3:
            self.pz = self.tz * self.Speed
            self.nbp = int(distance / (self.pas * self.Speed))
            print(self.nbp, distance, self.Speed, self.tz)

    def stepaxe(self, axis):
        if axis == 1:
            self.axis(1)
            time.sleep(self.pas)
            self.stop(1)
            self.px = self.pas * self.Speed

        elif axis == 2:
            self.axis(2)
            time.sleep(self.pas)
            self.stop(2)
            self.py = self.pas * self.Speed

        elif axis == 3:
            self.axis(3)
            time.sleep(self.pas)
            self.stop(3)
            self.pz = self.pas * self.Speed

    def stepend(self, axis, distance):
        if axis == 1:
            self.axis(1)
            time.sleep((distance - (self.nbp) * self.pas * self.Speed) / self.Speed)
            self.stop(1)
            self.px = distance - self.nbp * self.pas * self.Speed

        elif axis == 2:
            self.axis(2)
            time.sleep((distance - (self.nbp) * self.pas * self.Speed) / self.Speed)
            self.stop(2)
            self.py = distance - self.nbp * self.pas * self.Speed


        elif axis == 3:
            self.axis(3)
            time.sleep((distance - (self.nbp) * self.pas * self.Speed) / self.Speed)
            self.stop(3)
            self.pz = distance - self.nbp * self.pas * self.Speed

    def sleepback(self, axis):
        if axis == 1:
            self.tx = abs(self.position[0] / self.Speed)
            sleep(self.tx)
        elif axis == 2:
            self.ty = abs(self.position[1] / self.Speed)
            sleep(self.ty)
        elif axis == 3:
            self.tz = abs(self.position[2] / self.Speed)
            sleep(self.tz)

    def sleepgroupab(self, axis):
        for i in range(1, 4):
            if axis == i:
                if abs(self.v_position[i - 1]) <= self.course:
                    self.time[i - 1] = abs(self.v_position[i - 1] - self.position[i - 1]) / self.Speed
                    sleep(self.time[i - 1])

                elif self.v_position[i - 1] > self.course:
                    self.time[i - 1] = abs(self.course - self.position[i - 1]) / self.Speed
                    sleep(self.time[i - 1])
                    print('''limite de passe
''')
                elif abs(self.v_position[i - 1]) < -self.course:
                    self.time[i - 1] = abs(-self.course - self.position[i - 1]) / self.Speed
                    sleep(self.time[i - 1])
                    print('''limite de passe
''')

    def sleepgroupre(self, axis):
        for i in range(1, 4):
            position_f = [0, 0, 0]
            if axis == i:
                position_f[i - 1] = self.v_position[i - 1] + self.position[i - 1]
                if position_f[i - 1] > self.course:
                    self.time[i - 1] = abs(self.v_position[i - 1] - (position_f[i - 1] - self.course)) / self.Speed
                    sleep(self.time[i - 1])
                    print('''limite de passe
''')
                elif position_f[i - 1] < -self.course:
                    self.time[i - 1] = abs(self.v_position[i - 1] - (position_f[i - 1] + self.course)) / self.Speed
                    sleep(self.time[i - 1])
                    print('''limite de passe
''')
                elif abs(position_f[i - 1]) <= self.course:
                    self.time[i - 1] = abs(self.v_position[i - 1]) / self.Speed
                    sleep(self.time[i - 1])

    def pos(self):
        fichier = open("position.txt", "w")
        self.tto[0] = self.tto[0] + self.tx
        self.tto[1] = self.tto[1] + self.ty
        self.tto[2] = self.tto[2] + self.tz
        self.tx = self.ty = self.tz = 0
        self.position[0] = self.position[0] + self.px
        self.position[1] = self.position[1] + self.py
        self.position[2] = self.position[2] + self.pz
        self.px = self.py = self.pz = 0
        print("Position de la pointe de la pipette: " + str(self.position))
        fichier.write(str(self.position[0]) + ' ' + str(self.position[1]) + ' ' + str(self.position[2]))

    def cal(self):
        self.px = (self.tex - self.tbx) * self.Speed
        self.py = (self.tey - self.tby) * self.Speed
        self.pz = (self.tez - self.tbz) * self.Speed


#fichier = open("position.txt", "r")

#string = fichier.read()
#inter = string.split()


class Moteur(basic_fonctions):
    x = 0
    y = 0
    z = 0
    tx = 0  # Temps de fonctionnement
    ty = 0  # Temps de fonctionnement
    tz = 0  # Temps de fonctionnement
    Speed = 0
    px = 0  # Position de la pipette
    py = 0  # Position de la pipette
    pz = 0  # Position de la pipette
    tto = [tx, ty, tz]  # Vecteur de temps
    #position = [float(inter[0]), float(inter[1]), float(inter[2])]  # Vecteur de position
    position = [0,0,0]
    mstat = [0, 0, 0]
    v_distance = [0, 0, 0]
    v_position = [0, 0, 0]
    distance_group = [0, 0, 0]
    pas = 0
    nbp = 0  # nombre de pas
    tbx = 0  # temps de commencer x
    tex = 0  # temps de s'arrêter x
    tby = 0  # temps de commencer y
    tey = 0  # temps de s'arrêter y
    tbz = 0  # temps de commencer z
    tez = 0  # temps de s'arrêter z
    vitesse_r = 3 * 1 / 1.44  # tour/sec
    vitesse_l = 5000 * vitesse_r  # um/s
    vitesse_b = vitesse_l * 1.2  # um/s
    time = [0, 0, 0]

    def __init__(self):
        self.usbport = '/dev/tty.usbmodem14201'
        # self.usbport = '/dev/cu.usbmodem1A1321'
        self.myservo = serial.Serial(self.usbport, 9700, timeout=0)
        print('Get micro-servo moteur')

    def step(self, distance, mode, taille_pas, axis):
        self.Pas(taille_pas)
        self.steptime(axis, distance, taille_pas, mode)
        n = range(0, self.nbp)
        for i in n:
            print("Total number of steps: " + str(self.nbp) + " Step No: " + str(i + 1))
            self.stepaxe(axis)
            m.pos()
            # time.sleep(0.3)
        self.stepend(axis, distance)
        m.pos()
        print('done')

    def stop(self, axis):
        if axis == 1:
            self.myservo.write(b'x')
        elif axis == 2:
            self.myservo.write(b'y')
        elif axis == 3:
            self.myservo.write(b'w')
        elif axis == 0:
            self.myservo.write(b'0')
            print('All stopped')

    def gorelative(self, distance_d, axe):
        #  Choix de la vitesse #########
        distance = 0
        for i in range(1, 4):
            if distance_d == abs(distance):
                self.axis(i)
            elif distance_d == -abs(distance):
                self.axis(-i)
        print('vitesse ok')
        #  Calculer temps de d'avacement #######
        for i in range(1, 4):
            if axe == i:
                if abs(distance_d + self.position[i - 1]) <= self.course:
                    distance = distance_d
                    self.runtime(axe, distance)
                elif distance_d + self.position[i - 1] > self.course:
                    distance = distance_d - (self.position[i - 1] + distance_d - self.course)
                    self.runtime(axe, distance)
                    print('limite depasse')
                elif distance_d + self.position[i - 1] < -self.course:
                    distance = distance_d - (self.position[i - 1] + distance_d + self.course)
                    print(distance)
                    self.runtime(axe, distance)
                    print('limite depasse')

        # Choisir la direction #########
        self.pause(axe)
        self.stop(axe)
        self.pos()

    def goabsolue(self, destination, axis):
        # Choix de la vitesse #########
        self.sudu(2)
        print('vitesse at level 2')

        # Calculer temps de d'avacement #######
        for i in range(1, 4):
            if axis == i:
                if abs(destination) <= self.course:
                    distance = destination - self.position[i - 1]
                    self.runtime(axis, distance)
                elif destination > self.course:
                    distance = self.course - self.position[i - 1]
                    self.runtime(axis, distance)
                    print('limite depasse')
                elif destination < -self.course:
                    distance = -self.course - self.position[i - 1]
                    self.runtime(axis, distance)
                    print('limite depasse')

        if distance == abs(distance):
            self.axis(axis)
        else:
            self.axis(-axis)
        self.pause(axis)
        self.myservo.write('00')
        self.pos()

    def gma(self, vecteur_distance):
        # Choisir quelles axes à utiliser est donner les parametes##
        self.time = [self.tx, self.ty, self.tz]
        self.v_position = vecteur_distance
        #  Envoyer les commandes aux moteurs ####

        for i in range(0, 3):

            if self.v_position[i] - self.position[i] > 0:
                self.axis(i + 1)
            if self.v_position[i] - self.position[i] == 0:
                pass
            if self.v_position[i] - self.position[i] < 0:
                self.axis(-(i + 1))

        def x():
            self.sleepgroupab(1)
            self.stop(1)
            self.tx = self.time[0]
            print('''x get to position
            Toke ''' + str(self.tx) + '''s
            ''')
            if self.v_position[0] - self.position[0] < 0:
                self.px = -self.tx * self.Speed
            if self.v_position[0] - self.position[0] > 0:
                self.px = self.tx * self.Speed

        def y():
            self.sleepgroupab(2)
            self.stop(2)
            self.ty = self.time[1]
            print('''y get to position
            Toke ''' + str(self.ty) + '''s
            ''')
            if self.v_position[1] - self.position[1] < 0:
                self.py = -self.ty * self.Speed
            if self.v_position[1] - self.position[1] > 0:
                self.py = self.ty * self.Speed

        def z():
            self.sleepgroupab(3)
            self.stop(3)
            self.tz = self.time[2]
            print('''z get to position
            Toke ''' + str(self.tz) + '''s
            ''')
            if self.v_position[2] - self.position[2] < 0:
                self.pz = -self.tz * self.Speed
            if self.v_position[2] - self.position[2] > 0:
                self.pz = self.tz * self.Speed

        t1 = threading.Thread(target=x)
        t2 = threading.Thread(target=y)
        t3 = threading.Thread(target=z)

        t1.start()
        t2.start()
        t3.start()

        t1.join()
        t2.join()
        t3.join()

        self.pos()

    def gmr(self, vecteur_distance):
        self.time = [self.tx, self.ty, self.tz]
        self.v_position = vecteur_distance

        # Envoyer les commandes aux moteurs ####
        for i in range(0, 3):

            if self.v_position[i] > 0:
                self.axis(i + 1)
            if self.v_position[i] == 0:
                pass
            if self.v_position[i] < 0:
                self.axis(-(i + 1))

        def x():
            self.sleepgroupre(1)
            self.stop(1)

            self.tx = self.time[0]
            print('x get to position Toke ' + str(self.tx) + 's' + '''
''')
            if self.v_position[0] < 0:
                self.px = -self.tx * self.Speed
            elif self.v_position[0] > 0:
                self.px = self.tx * self.Speed

        def y():
            self.sleepgroupre(2)
            self.stop(2)
            self.ty = self.time[1]
            print('y get to position Toke ' + str(self.ty) + 's' + '''
''')
            if self.v_position[1] < 0:
                self.py = -self.ty * self.Speed
            elif self.v_position[1] > 0:
                self.py = self.ty * self.Speed

        def z():
            self.sleepgroupre(3)
            self.stop(3)
            self.tz = self.time[2]
            print('z get to position Toke ' + str(self.tz) + 's' + '''
''')
            if self.v_position[2] < 0:
                self.pz = -self.tz * self.Speed
            elif self.v_position[2] > 0:
                self.pz = self.tz * self.Speed

        t1 = threading.Thread(target=x)
        t2 = threading.Thread(target=y)
        t3 = threading.Thread(target=z)

        t1.start()
        t2.start()
        t3.start()

        t1.join()
        t2.join()
        t3.join()

        self.pos()

    def zero(self):
        if self.position[0] > 0:
            self.axis(-1)
        if self.position[0] < 0:
            self.axis(1)
        if self.position[1] > 0:
            self.axis(-2)
        if self.position[1] < 0:
            self.axis(2)
        if self.position[2] > 0:
            self.axis(-3)
        if self.position[2] < 0:
            self.axis(3)

        def one():
            self.sleepback(1)
            self.stop(1)

            print('''x get to 0
''')
            if self.position[0] < 0:
                self.px = self.tx * self.Speed
            if self.position[0] > 0:
                self.px = -self.tx * self.Speed

        def two():
            self.sleepback(2)
            self.stop(2)
            print('''y get to 0
''')
            if self.position[1] < 0:
                self.py = self.ty * self.Speed
            if self.position[1] > 0:
                self.py = -self.ty * self.Speed

        def three():
            self.sleepback(3)
            self.stop(3)
            print('''z get to 0
                ''')
            if self.position[2] < 0:
                self.pz = self.tz * self.Speed
            if self.position[2] > 0:
                self.pz = -self.tz * self.Speed

        t1 = threading.Thread(target=one)
        t2 = threading.Thread(target=two)
        t3 = threading.Thread(target=three)

        t1.start()
        t2.start()
        t3.start()

        t1.join()
        t2.join()
        t3.join()

        m.pos()

    def setpos(self, cx, cy, cz):
        self.position[0] = cx
        self.position[1] = cy
        self.position[2] = cz
        self.pos()

    def check(self):
        m.sudu(5)
        self.axis(1)
        self.axis(2)
        self.axis(3)
        time.sleep(1)
        self.axis(-1)
        self.axis(-2)
        self.axis(-3)
        time.sleep(1)
        self.stop(0)

    def precision(self):
        m.gmr((200, 200, 500))
        time.sleep(2)
        m.zero()


if __name__ == '__main__':
    m = Moteur()
    time.sleep(4)
    i = 3
    m.axis(1)
    time.sleep(i)
    m.axis(-1)
    time.sleep(i)
    m.stop(1)
    m.axis(2)
    time.sleep(i)
    m.axis(-2)
    time.sleep(2)
    m.stop(2)
    m.axis(3)
    time.sleep(i)
    m.axis(-3)
    time.sleep(i)
    m.stop(3)


