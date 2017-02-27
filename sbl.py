#!/usr/bin/env/python
# sbl.py
# Ein Launcher für den Soutibot. Wenn per Shell aufgerufen, kann als Argument
# das zu verwendende Homeverzeichnis angegeben werden.
#
# Letztes Update: 16.01.2017 (Config eingebaut)

import soutibot
import sys
import os
import json

config = { "homedir" : "/home/pi",
        "muckedir" : "mucke",
        "configdir" : ".soutibot_config",
        "apitokenfile" : "apitoken.txt",
        "networkdevicename" : "wlan0"}

def initial_setup():
    global config
    print("Willkommen zum Soutibot-Setup!")

    homedir = input("Homeverzeichnis? (Vorgabe: " + config["homedir"] + ") ")
    if (homedir == ""):
        homedir = config["homedir"]
    if (os.path.isdir(homedir + "/")):
        if (os.access(homedir, os.W_OK | os.X_OK | os.R_OK)):
            config["homedir"] = homedir
        else:
            print("Fehler: Kein Zugriff!")
            return False
    else:
        print("Fehler: Kein Verzeichnis")
        return False

    inputdir = input("Musikordner? (Vorgabe: " + config["muckedir"] + ") ")
    if (inputdir == ""):
        muckedir = config["homedir"] + "/" + config["muckedir"]
    else:
        muckedir = config["homedir"] + "/" + inputdir

    if (not os.path.isdir(muckedir + "/")):
        a = input("Verzeichnis existiert nicht. Neu erstellen? (j/n) ").lower()
        if (a == "j" or a == "y"):
            if(os.access(muckedir, os.R_OK)):
                os.mkdir(muckedir)
                config["muckedir"] = muckedir
            else:
                print("Fehler: Kein Zugriff!")
                return False
        else:
            return False
    else:
        if(os.access(muckedir, os.R_OK)):
            config["muckedir"] = muckedir
        else:
            print("Fehler: Kein Zugriff!")

    atf = input("Datei mit dem API-Token? (Vorgabe: " + config["apitokenfile"] + ") ")
    if (atf != ""):
        config["apitokenfile"] = atf
        print("Bitte speichere das API-Token in dieser Datei!")
    
    ndn = input("Name der Netzwerkkarte? (Vorgabe: " + config["networkdevicename"] + ") ")
    if (ndn != ""):
        config["networkdevicename"] = ndn

    f = open("config.txt", "w")
    json.dump(config, f)
    f.close()

    return True

def load_config():
    global config
    f = open("config.txt")
    config = json.load(f)
    f.close()

def launch_bot():
    global config
    s = soutibot.Soutibot(config)
    try:
        print("Soutibot wird gestartet!")
        s.start()
    except (KeyboardInterrupt):
        print("Soutibot wird beendet...")
        s.shutdown()

if (__name__ == "__main__"):
    if (len(sys.argv) > 1):
        option = sys.argv[1]
        if (option == "-i"):
            if(initial_setup()):
                print("Setup abgeschlossen!")
            else:
                print("Setup fehlgeschlagen!")
    else:
        print("Moin, ich bin der Soutibot-Launcher.")
        if (os.path.isfile("config.txt")):
            load_config()
            launch_bot()
        else:
            print("config.txt existiert nicht. Für das erstmalige Setup des Bots" +
                    " bitte 'python sbl.py -i' aufrufen.")
