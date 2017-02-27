# playbackmgr.py
# Stellt eine Klasse zur Verfügung, welche der Soutibot benutzt, um Musik
# abzuspielen. Dies geschieht in einem separaten Thread.
#
# Letztes Update: 16.01.2017 (Code kommentiert)

# Damit ein eigener Thread für den Player erstellt werden kann
from threading import Thread

# Falls gerade nichts zu tun ist, kann der Manager kurz schlafen
import time

# Damit shell-Kommandos (mplayer) ausgeführt werden können
from subprocess import *

import logging

# Um das Dateisystem nach Musik zu durchsuchen
import os

# Damit die Playlist bei Bedarf durchgemischt werden kann
import random

from mpd import MPDClient, ConnectionError

import urllib.parse

class PlaybackManager():
    """This is a PlaybackManager. It manages Playback.
    """

    running = False # Loift oder loift nicht
    SLEEPTIME = 0.1 # Kurz mal pennen gehen
    track_queue = [] # Die Wiedergabeliste
    current_track = "" # Der aktuelle Track
    volume = 100 # Die derzeitige Lautstärke
    muckedir = "" # Der Ordner mit Musik drin

    @staticmethod
    def start(directory):
        """Initialisiert den Playbackmanager und spawnt einen separaten Thread.
        """

        PlaybackManager.muckedir = directory
        PlaybackManager.the_client = MPDClient()
        client = PlaybackManager.the_client
        client.timeout = 10
        client.idletimeout = None
        client.connect("192.168.178.47", 6660)
        client.consume(1)
        client.random(0)

        logging.info("PlaybackManager loift!")

    @staticmethod
    def client():
        try:
            PlaybackManager.the_client.ping()
        except ConnectionError:
            print("Verbinde neu...")
            PlaybackManager.the_client.connect("192.168.178.47", 6660)
        return PlaybackManager.the_client

    @staticmethod
    def current_track():
        client = PlaybackManager.client()
        track = client.currentsong()
        if (track == {}):
            return ""
        tokens = track["file"].split("/")
        result = urllib.parse.unquote(tokens[len(tokens)-1])

        return result

    @staticmethod
    def print_queue():
        """Gibt eine Liste der Tracks aus, die als nächstes gespielt werden.
        """
        
        result = ""
        client = PlaybackManager.client()
        tracks = client.playlist()
        for track in tracks:
            if(track[:6] == " local"):
                tokens = track.split("/")
                result = result + urllib.parse.unquote(tokens[len(tokens)-1]) + "\n"

        current = PlaybackManager.current_track()

        return current + "\n" + result.split(current)[1]

    @staticmethod
    def query(request, shuffle):
        """Hängt Musik an die Warteschlange, wenn request in der Sammlung
        gefunden wird. Mit shuffle wird die Musik durchgemischt.
        """

        client = PlaybackManager.client()
        result = (PlaybackManager.search(request))
        for track in result:
            client.add(client.search("filename", urllib.parse.quote(track))[0]['file'])

    @staticmethod
    def search(request):
        result = []
        client = PlaybackManager.client()
        tracks = client.search("any", request)
        for track in tracks:
            tokens = track["file"].split("/")
            result.append(urllib.parse.unquote(tokens[len(tokens)-1]))

        return result

    @staticmethod
    def play_queue():
        """Läuft in einer Endlosschleife, bis running auf False gesetzt wird.
        Spielt die Wiedergabeliste ab, falls es eine gibt.
        """

        while (PlaybackManager.running):
            PlaybackManager.p.poll() # returncode aktualisieren
            if (PlaybackManager.p.returncode != None): # terminiert?
                PlaybackManager.current_track = ""
                if (len(PlaybackManager.track_queue) > 0):
                    PlaybackManager.current_track = PlaybackManager.track_queue[0]
                    PlaybackManager.play_track(PlaybackManager.current_track)
                    del PlaybackManager.track_queue[0]
                else:
                    time.sleep(PlaybackManager.SLEEPTIME)

    @staticmethod
    def playpause():
        client = PlaybackManager.client()
        state = client.status()["state"]
        if (state == "play"):
            client.pause()
        if (state == "pause" or state == "stop"):
            client.play()
        state = client.status()["state"]
        return state


    @staticmethod
    def skip(number):
        """Überspringt number Tracks inklusive dem aktuellen. Falls weniger
        Musik eingereiht ist, stoppt die Wiedergabe.
        """
        client = PlaybackManager.client()
        for i in range(number):
            client.next()

    @staticmethod
    def get_volume():
        client = PlaybackManager.client()
        volume = client.status()["volume"]
        return int(volume)
   
    @staticmethod
    def set_volume(number):
        """Setzt die Lautstärke auf number. Möglicherweise muss für andere
        Geräte der Name des Audiogeräts angepasst werden.
        """
        client = PlaybackManager.client()
        client.setvol(number)

    @staticmethod
    def increase_volume():
        """Erhöht die Lautstärke um 5%
        """

        number = min(PlaybackManager.get_volume()+5, 100)
        PlaybackManager.set_volume(number)

    @staticmethod
    def decrease_volume():
        """Verringert die Lautstärke um 5%
        """

        number = max(PlaybackManager.get_volume()-5, 0)
        PlaybackManager.set_volume(number)

    @staticmethod
    def print_volume():
        """Gibt die aktuelle Lautstärke aus
        """

        return "Die Lautstärke ist derzeit auf " + str(PlaybackManager.get_volume()) + "% eingestellt."

    @staticmethod
    def stop():
        """Beendet den PlaybackManager.
        """

        logging.info("PlaybackManager wird gestoppt.")
        client = PlaybackManager.client()
        client.close()
        client.disconnect()
