import socket
from sys import byteorder
import time
import random
import zlib
import math
import os
import threading


IP_ADD = socket.gethostbyname(socket.gethostname())                 #zistenie IP adresy

LEN_DATA = 0
                                        
keep_alive = False

class Hlavicka: 
    def __init__(self, flag, pocet_paketov=0, cislo_paketu=0, crc=0, data=''):                  #uvodna inicializacia udajov
        self.flag = flag
        self.pocet_paketov = pocet_paketov
        self.cislo_paketu = cislo_paketu
        self.crc = crc
        self.data = data

        self.flag = flag.to_bytes(1, byteorder='big')                                           #prehodim vsetko na bajty s potrebnou velkostou 
        self.pocet_paketov = pocet_paketov.to_bytes(2, byteorder='big')
        self.cislo_paketu = cislo_paketu.to_bytes(2, byteorder='big')
        self.crc = crc.to_bytes(4, byteorder='big')

def vytvor_packet(flag,pocet_paketov=0, cislo_paketu=0, crc=0, data='', nazov_suboru=''):       
    if((flag==0 or flag==2 or flag==6) and nazov_suboru==''):
        return Hlavicka(flag)                                                                   #vrati typ bud 0 - nadviazanie spojenia, 2 - Keep Alive, 6 - Ukoncenie spojenia
    elif((flag!=0 and flag!=2 and flag!=6) and nazov_suboru==''):
        return Hlavicka(flag, pocet_paketov,cislo_paketu, crc, data)                            #vrati ti spravu
    else:
        return Hlavicka(flag, pocet_paketov, cislo_paketu, crc, nazov_suboru)                   #vrati subor
    
def decode_packet(Frame_hlavicka):
    flag = int.from_bytes(Frame_hlavicka[:1], byteorder='big')
    pocet_paketov = int.from_bytes(Frame_hlavicka[1:3],byteorder='big')
    cislo_paketu = int.from_bytes(Frame_hlavicka[3:5], byteorder='big')
    crc= int.from_bytes(Frame_hlavicka[5:9], byteorder='big')
    data = Frame_hlavicka[9:]
    return flag, pocet_paketov, cislo_paketu, crc, data

def KeepAlive(destination_socket, client_destination_address):                              #thread.start bezi na pozadi a thread.join() ked sa spusti tak sa spusti thread a program caka kym neskonci
    global keep_alive
    time.sleep(0.01)

    while True:
        data = vytvor_packet(2)
        data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc
        destination_socket.sendto(data, client_destination_address)                           #posleme keep alive serveru

        try:                                                            #cakame na odpoved od servera, ci pride KA alebo nie
            destination_socket.settimeout(15)
            data, client_destination_address = destination_socket.recvfrom(1500)
        except (ConnectionResetError, socket.timeout):
            if (not keep_alive):
                return
            print("Neprisiel keep alive")
            destination_socket.close()
            keep_alive=False
            return 0
        
        flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)  #ak prisiel paket, dekoduj
        if(flag!=2):                                                        #ak prišiel iný flag paketu, tak ukonči
            print("Prisiel nespravny Keep Alive")
            keep_alive=False
            destination_socket.close()
            return

        print("Ostava spojenie")                                            #inak ostava spojenie nastavené na 5 sekúnd 
        for i in range(0,5):
            time.sleep(1)
            if (keep_alive==0):
                return

def posliData(client_sock, kolko_fragmentov, pocet_chybnych_fragmentov, velkost_fragmentu, sprava, client_destination_address, volba_klient):
    cislo_fragmentu=1
    while True:

        if(volba_klient==1):                                                                        #sprava

            while True:
                
                try:
                    cast_spravy = sprava[(cislo_fragmentu-1)*velkost_fragmentu:cislo_fragmentu*velkost_fragmentu]
                except IndexError:
                    cast_spravy = sprava[(cislo_fragmentu-1)*velkost_fragmentu]

                crc = zlib.crc32(cast_spravy)

                if(pocet_chybnych_fragmentov>0):                                    #tu sa dobra sprava meni na zlu spravu
                    dobra_sprava = cast_spravy
                    random_cislo = random.randint(0,len(cast_spravy)-1)
                    cast_spravy = cast_spravy[0:random_cislo]
                    pocet_chybnych_fragmentov = pocet_chybnych_fragmentov-1

                
                data = vytvor_packet(3, kolko_fragmentov, cislo_fragmentu, crc, cast_spravy)
                #print(data.pocet_paketov, data.cislo_paketu, data.data)
                data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                client_sock.sendto(data, client_destination_address)                      
                data, client_destination_address = client_sock.recvfrom(1500)
                flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)

                if(flag==5):                                                        #dosiel chybny paket a teda dojde dobry paket
                    
                    data = vytvor_packet(3, kolko_fragmentov, cislo_fragmentu, crc, dobra_sprava)
                    data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                    client_sock.sendto(data, client_destination_address)
                    data, client_destination_address = client_sock.recvfrom(1500)
                    flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)


                if(kolko_fragmentov==cislo_fragmentu):              #vsetko sa poslalo
                    print("vsetky data sa poslali")
                    return
                else:
                    cislo_fragmentu = cislo_fragmentu+1
        
        elif(volba_klient==2):                                                                      #subor
            while True:
                
                try:
                    cast_suboru = sprava[(cislo_fragmentu-1)*velkost_fragmentu:cislo_fragmentu*velkost_fragmentu]
                except IndexError:
                    cast_suboru = sprava[(cislo_fragmentu-1)*velkost_fragmentu]

                crc = zlib.crc32(cast_suboru)

                if(pocet_chybnych_fragmentov>0):                                    #tu sa dobra sprava meni na zlu spravu
                    dobra_sprava = cast_suboru
                    random_cislo = random.randint(0,len(cast_suboru)-1)
                    cast_suboru = cast_suboru[0:random_cislo]
                    pocet_chybnych_fragmentov = pocet_chybnych_fragmentov-1

                
                data = vytvor_packet(4, kolko_fragmentov, cislo_fragmentu, crc, cast_suboru)
                #print(data.pocet_paketov, data.cislo_paketu, data.data)
                data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                client_sock.sendto(data, client_destination_address)                              #stop and wait
                data, client_destination_address = client_sock.recvfrom(1500)
                flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data) 

                if(flag==5):                                                        #dosiel chybny paket a teda dojde dobry paket
                    
                    data = vytvor_packet(3, kolko_fragmentov, cislo_fragmentu, crc, dobra_sprava)
                    data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                    client_sock.sendto(data, client_destination_address)
                    data, client_destination_address = client_sock.recvfrom(1500)
                    flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)
                    

                if(kolko_fragmentov==cislo_fragmentu):              #vsetko sa poslalo
                    print("Vsetky data sa poslali")
                    return
                else:
                    cislo_fragmentu = cislo_fragmentu+1
        
def pocuvajData(server_sock, flag, pocet_packetov, nazov_suboru):

    global LEN_DATA

    if(flag==3):                                                                                        #sprava
        print("PRICHADZA SPRAVA")
        print("PRICHADZAJU PAKETY")
        fragmenty = [] 
        while len(fragmenty)<pocet_packetov:
            data, server_destination_address = server_sock.recvfrom(1500)

            LEN_DATA += len(data[0:9])

            flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)


            print(f"{cislo_paketu}. fragment: {data.decode('utf-8')} ")
                                                                                                        #stop and wait arq metoda
            aktualne_crc = zlib.crc32((data))

            if(aktualne_crc==crc):
                print("Spravny paket")
                neprepisane_data=data
                data = vytvor_packet(1, pocet_paketov, cislo_paketu, crc, data)                         
                data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                server_sock.sendto(data, server_destination_address)
                fragmenty.append(neprepisane_data.decode())
            else:
                print("Nespravny paket, pytam znova")
                data = vytvor_packet(5, pocet_paketov, cislo_paketu, crc, data)                         
                data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                server_sock.sendto(data, server_destination_address)
        
        print(''.join(fragmenty))                                                                        #vypise na konci zadanu spravu 

    if(flag==4):                                                                                        #subor
        print("PRICHADZA SUBOR")
        print("PRICHADZAJU PAKETY")
        fragmenty = [] 
        while len(fragmenty)<pocet_packetov:
            data, server_destination_address = server_sock.recvfrom(1500)

            LEN_DATA += len(data[0:9])

            flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)

            

            print(f"{cislo_paketu}. fragment: {len(data)} ")

            aktualne_crc = zlib.crc32((data))                                                            #stop and wait arq metoda

            if(aktualne_crc==crc):
                print("Spravny paket")
                neprepisane_data=data
                data = vytvor_packet(1, pocet_paketov, cislo_paketu, crc, data)                        
                data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                server_sock.sendto(data, server_destination_address)
                fragmenty.append(neprepisane_data)
            else:
                print("Nespravny paket, pytam znova")
                data = vytvor_packet(5, pocet_paketov, cislo_paketu, crc, data)                         
                data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
                server_sock.sendto(data, server_destination_address)
        nazov_suboru = nazov_suboru.decode()

        sprava = fragmenty[0]
        for i in range(1, len(fragmenty)):
            sprava += fragmenty[i]
        with open(nazov_suboru, "wb") as f:
            f.write(sprava)
        print("Subor bol spravne ulozeny.")

def server():                                                       #funkcia server

    global LEN_DATA

    server_port = int(input("Zadaj port serveru: "))

    addr = ("", server_port)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.settimeout(60)                                          #nastavime cas na 60s
    server_sock.bind(addr)

    try:                                                                #pokial nevyprsi nastaveny cas 60s
        data, server_destination_address = server_sock.recvfrom(1500)

        LEN_DATA += len(data[0:9])
        
        flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)
        

        if(flag==0):                                                    #ak je flag 0, nadviaze spojenie
            print(f"WE ESTABLISH CONNECTION WITH ADDRESS {server_destination_address}")
            server_sock.sendto(data, server_destination_address)
            server_start(server_sock)
            return
        else:                                                           #inak sa spojenie nenadviaze
            print(f"CONNECTION COULD NOT BE ESTABLISHED")
            server_sock.close()                                         #spojenie sa uzavrie
            return
    except socket.timeout:
        print(f"DISCONNECTION")
        server_sock.close()
        return

def server_start(server_sock):

    global LEN_DATA

    while True:
        print("SERVER MENU: ")
        print("1 - ZMENA ROLY, 2 - POKRACOVAT, 3 - UKONCIT")
        volba_server = input("Vyber si moznost: ")

        server_sock.settimeout(60)

        if(volba_server==str(1)):
            client_start(server_sock, server_destination_address)
        elif(volba_server==str(2)):
            print(f"Pokracujeme")
        elif(volba_server==str(3)):
            print(f"SERVER SA VYPINA")
            
            print("Celková velkost rezie je: ", LEN_DATA, " B")

            server_sock.close()
            return
            
        try:
            while True:
                data, server_destination_address = server_sock.recvfrom(1500)

                LEN_DATA += len(data[0:9])

                flag, pocet_paketov, cislo_paketu, crc, data_msg = decode_packet(data)
                

                if(flag==1):                                                #Ak flag == 1, tak potvrdi uspesne a spravne dorucenie paketu
                    server_sock.sendto(data, server_destination_address)
                elif(flag==2):                                              #Ak flag == 2 , tak ide KA sprava
                    server_sock.sendto(data, server_destination_address)
                elif(flag==3):                                              #Ak flag == 3 , tak sa ide posielat sprava
                    pocuvajData(server_sock, flag, pocet_paketov, data)
                    break
                elif(flag==4):                                              #Ak flag == 4, tak sa ide posielat subor
                    final_cesta=input("Zadaj, kam chces vlozit subor: ")
                    nazov_suboru = data_msg
                    if(final_cesta!='.'):
                        nazov_suboru = os.path.join(final_cesta.encode(), nazov_suboru)
                    pocuvajData(server_sock, flag, pocet_paketov, nazov_suboru)
                    print("Subor bol ulozeny na ceste: ",os.path.abspath(final_cesta))
                    break
                elif(flag==6):                                              #Ak flag== 6 , tak nastane ukoncenie spojenia
                    print(f"Server ukoncil komunikaciu")
                    server_sock.close()                                     #Spojenie sa uzavrie 
                    return
        except socket.timeout:
            print("DISCONNECTION")
            server_sock.close()
            break    

def client():                                                       #funkcia klient


    print(IP_ADD)
    ipcka = input("Zadaj IP adresu: ")

    port = int(input("Zadaj port servera: "))
    client_destination_address = (ipcka, port)

    client_sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = vytvor_packet(0)                                                 #vytvori paket
    data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc    #naplnime ho
    client_sock.sendto(data, client_destination_address)

    data, client_destination_address = client_sock.recvfrom(1500)
    flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)
    if(flag==0):                                                        #ak je flag 0 , nadviaze spojenie na danom porte
        print(f"WE ARE CONNECTED WITH ADDRESS: {ipcka, port}")
        client_start(client_sock, client_destination_address)
    else:                                                               #inak sa spojenie nenadviaze a spojenie sa uzavrie
        print(f"CONNECTION COULD NOT BE ESTABLISHED")
        client_sock.close()
        return

def client_start(client_sock, client_destination_address):

    global keep_alive
    thread1 = None

    while True:

        if not keep_alive:
            keep_alive = True
            thread1 = threading.Thread(target=KeepAlive, args=(client_sock, client_destination_address))
            thread1.start()

        print("KLIENT MENU: ")
        print("1 - POSLAT SPRAVU, 2 - POSLAT SUBOR, 3 - ZMENA ROLY, 4 - UKONCIT")
        volba_klient = input("Vyber si moznost: ")

        if(volba_klient==str(1)):                                                   #ak chcem posielat spravu 

            refresh = False
            if keep_alive:                                                          #vypneme Keep Alive
                refresh = True
                keep_alive = False
                thread1.join()

            data = vytvor_packet(1)                                                 #vytvori paket
            data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc    #naplnime ho
            client_sock.sendto(data, client_destination_address)         
            data, client_destination_address = client_sock.recvfrom(1500)
            flag, pocet_paketov, cislo_paketu, crc, data = decode_packet(data)

            sprava = input("Zadaj spravu: ").encode()

            velkost_fragmentu = int(input("Zadaj velkost fragmentu [1 - 1463]: "))
            while(velkost_fragmentu<1 or velkost_fragmentu>1463):
                print("Zadal si nespravnu hodnotu")
                velkost_fragmentu = int(input("Zadaj velkost fragmentu [1 - 1463]: "))

            pocet_fragmentov = math.ceil(len(sprava) / velkost_fragmentu)                   #math ceil - zaokruhlenie nahor, v pripade ze mam presah

            data = vytvor_packet(3, pocet_fragmentov)
            data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc
            client_sock.sendto(data, client_destination_address)
            print(f"{pocet_fragmentov} bude poslanych")

            pocet_chybnych_fragmetnov = int(input("Zadaj pocet chybnych fragmentov: "))
            if(pocet_chybnych_fragmetnov>pocet_fragmentov):
                while True:
                    int(input("Zadal si zlu hodnotu, zadaj znovu pocet chybnych fragmentov: "))

            posliData(client_sock, pocet_fragmentov, pocet_chybnych_fragmetnov,velkost_fragmentu, sprava, client_destination_address, 1)

            if refresh:                                                                    #zapneme KA 
                keep_alive = True
                thread1 = threading.Thread(target=KeepAlive, args=(client_sock, client_destination_address))
                thread1.start()
            
        elif(volba_klient==str(2)):                                                     #ak chcem poslat subor

            refresh = False
            if keep_alive:                                                          #vypneme Keep Alive
                refresh = True
                keep_alive = False
                thread1.join()

            data = vytvor_packet(1)                                                 #vytvori paket
            data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc    #naplnime ho
            client_sock.sendto(data, client_destination_address)
            data, client_destination_address = client_sock.recvfrom(1500)

            subor=''                                                                    
            subor = input("Zadaj cestu suboru: ")   
            while os.path.exists(subor) is False:
                print("Taka cesta neexistuje")
                subor = input("Zadaj cestu suboru: ")

            with open(subor, "rb") as f:                                                #precitanie suboru
                sprava = f.read()     

            nazov_suboru = subor[subor.rfind('\\')+1:]                                                 #hlada mi to posledny vyskyt(prvy sprava) - teda nazov suboru

            velkost_fragmentu = int(input("Zadaj velkost fragmentu [1 - 1463]: "))
            while(velkost_fragmentu<1 or velkost_fragmentu>1463):
                print("Zadal si nespravnu hodnotu")
                velkost_fragmentu = int(input("Zadaj velkost fragmentu [1 - 1463]: "))

            pocet_fragmentov = math.ceil(len(sprava) / velkost_fragmentu)                   #math ceil - zaokruhlenie nahor, v pripade ze mam presah a +1 preto, lebo prvy fragment bude nazov suboru

            data = vytvor_packet(4, pocet_fragmentov, 0, 0, ' ', nazov_suboru.encode())                 #uvedomim server, ze idem poslat subor
            data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc + data.data
            client_sock.sendto(data, client_destination_address)
            print(f"{pocet_fragmentov} bude poslanych")

            pocet_chybnych_fragmetnov = int(input("Zadaj pocet chybnych fragmentov: "))

            while (pocet_chybnych_fragmetnov>pocet_fragmentov or pocet_chybnych_fragmetnov<0):
                int(input("Zadal si zlu hodnotu, zadaj znovu pocet chybnych fragmentov: "))

            posliData(client_sock, pocet_fragmentov, pocet_chybnych_fragmetnov, velkost_fragmentu, sprava, client_destination_address, 2)

            if refresh:
                keep_alive = True
                thread1 = threading.Thread(target=KeepAlive, args=(client_sock, client_destination_address))
                thread1.start()

        elif(volba_klient==str(3)):
            if keep_alive:                                                          #vypnem keep alive
                keep_alive = False
                thread1.join()
            server_start(client_sock)

        elif(volba_klient==str(4)):                                                     #Ak chcem ukoncit spojenie
            data = vytvor_packet(6)
            data = data.flag + data.pocet_paketov + data.cislo_paketu + data.crc
            client_sock.sendto(data, client_destination_address)
            if keep_alive:
                keep_alive = False
                thread1.join()
            print(f"Ukoncujem spojenie")
            client_sock.close()
            break

def main():
    
    pom = input("Vyber si: 1 - SERVER | 2 - KLIENT | 3 - UKONCENIE PROGRAMU ")
    if(pom == str(1)):
        server()
    elif(pom == str(2)):
        client()
    elif(pom == str(3)):
        print("UKONCUJEM PROGRAM")

main()