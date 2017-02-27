# soutibot.py
# Dieses Modul stellt die Klasse Soutibot zur Verfügung, welche für die
# zentrale Steuerung desselbigen Verantwortlich ist.
# 
# Letztes Update: 16.01.2017 (Code kommentiert)
#
# TODO (ungefähr in der Reihenfolge, die ich für sinnvoll halte):
# -Steuerbarer Player: Pause
# -Besseres User-Interface (Nachricht bei erfolgreichem Download etc.)
# -Mediathek-Verwaltung
# -Musiksammlung anzeigen
# -Dynamische Warteschlangenverwaltung
# -Voting
# -Bluetooth-Modus
# -Spotify-Integration
# -Display einrichten

# Modul, welches Möglichkeiten bereitstellt, bequem mit der 
# Telegram-Bot-API zu kommunizieren
import telepot

# Wird benötigt, um mit Inline-Keyboards zu antworten
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

# Modul, mit dem Downloads von YouTube-Videos erledigt werden können.
# Damit es funktioniert, muss außerdem das Modul youtube-dl installiert sein.
import pafy

# Um Shell-Befehle auszuführen (z.B. mplayer)
from subprocess import *

# Um den Bot am Laufen zu halten, wird time.sleep() benötigt
import time

# Für Dateikram
import os

# Damit unbenannte Dateien eine zufällige Nummer bekommen können:
import random

import json

import logging

# Separate Klasse zum Verwalten von Downloads (YouTube und Musikateien)
import downloadmgr

# Separate Klasse zur Steuerung der abgespielten Musik
import playbackmgr

class Soutibot():
    """Diese Klasse implementiert die Kernfunktionen des Soutibot.
    Bestimmte Module wurden in externe Klassen ausgelagert.
    """
    default_config = { "allow_skip" : True,
                        "logging_level" : "DEBUG",
                        "admin_pw" : "eigenuran"}

    config = {}

    admins = []

    # API-Token, welches für die Kommunikation mit der Telegram-API benötigt
    # wird. Muss für die Verwendung eines anderen Bots angepasst werden.
    apitoken = ""

    # Homeverzeichnis. Wird bei Initialisierung gesetzt.
    homedir = ""
    muckedir = ""
    configdir = ""
    configfile = ""
    networkdevicename = ""

    def __init__(self, config):
        """Startet alle Services, die im Hintergrund laufen müssen. Danach
        kann mit der start()-Methode der Bot gestartet werden.
        """

        # Ordner einrichten
        Soutibot.homedir = config["homedir"]
        Soutibot.muckedir = config["muckedir"]
        Soutibot.configdir = Soutibot.homedir + "/" + config["configdir"]
        if (not os.path.isdir(Soutibot.configdir)):
            os.mkdir(Soutibot.configdir)

        # Configdateien einrichten
        Soutibot.configfile = Soutibot.configdir + "/config.txt"
        if (not os.path.isfile(Soutibot.configfile)):
            f = open(Soutibot.configfile, "w")
            json.dump(Soutibot.default_config, f)
            f.close()
            Soutibot.config = Soutibot.default_config
        else:
            f = open(Soutibot.configfile)
            Soutibot.config = json.load(f)
            f.close()
        
        Soutibot.adminsfile = Soutibot.configdir + "/admins.txt"
        if (not os.path.isfile(Soutibot.adminsfile)):
            f = open(Soutibot.adminsfile, "w")
            json.dump(Soutibot.admins, f)
            f.close()
        else:
            f = open(Soutibot.adminsfile)
            Soutibot.admins = json.load(f)
            f.close()

        # Logger einrichten
        now = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        logfile = Soutibot.configdir + "/logs/" + now + ".log"
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                            datefmt='%d.%m.%Y %H:%M:%S',
                            level=self.config["logging_level"],
                            filename = logfile)


        Soutibot.networkdevicename = config["networkdevicename"]
        f = open(config["apitokenfile"])
        Soutibot.apitoken = json.load(f)
        f.close()

        logging.info("Der Soutibot ist bereit.")

        Soutibot.bot = telepot.Bot(Soutibot.apitoken) # Initialisiere Bot
        self.dlm = downloadmgr.DownloadManager
        self.pbm = playbackmgr.PlaybackManager
        self.dlm.start()
        self.pbm.start(Soutibot.muckedir)

    @staticmethod
    def get_ip():
        """Gibt die IP des Pi zurück, falls dieser mit dem Internet verbunden
        ist. Wichtig ist hier, dass der Name der Netzwerkkarte bekannt ist.
        """

        cmd = "ip addr show " + Soutibot.networkdevicename
        cmd += " | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"

        p = Popen(cmd, shell=True, stdout=PIPE)
        return p.communicate()[0].ljust(16)

    @staticmethod
    def send_message(user, message):
        """Sendet die Nachricht message an den Telegram-User mit der ID user.
        """

        Soutibot.bot.sendMessage(user, message)

    def on_chat_message(self, msg):
        """Wird ausgeführt, wenn der Bot eine Chatnachricht empfängt.
        """

        content_type, chat_type, chat_id = telepot.glance(msg) # Eckdaten checken

        # Je nach Typ des Inhalts muss die Nachricht anders behandelt werden:
        if (content_type == "text"):
            self.handle_textmessage(msg, chat_id)
        if (content_type == "audio"):
            self.handle_audiofile(msg["audio"], chat_id)

    def on_callback_query(self, msg):
        """Wird ausgeführt, wenn jemand auf einen Button einer Inline-Tastatur
        drückt, die an eine Nachricht angehängt ist.
        """

        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        message_id = msg["message"]["message_id"]

        # Hier wird das aufgerufene Kommando abgefragt und ausgeführt
        if (query_data == "cmd_refresh"):
            try:
                self.bot.editMessageText((from_id, message_id), 
                        self.controller_message(), reply_markup=self.controller_keyboard())
                self.bot.answerCallbackQuery(query_id)
            except telepot.exception.TelegramError:
                self.bot.answerCallbackQuery(query_id, text="Die Warteschlange ist bereits aktuell.")

        if (query_data == "cmd_playpause"):
            result = self.pbm.playpause()
            if (result == "play"):
                self.bot.answerCallbackQuery(query_id, text='Musik wird abgespielt...')
            elif (result == "pause"):
                self.bot.answerCallbackQuery(query_id, text='Wiedergabe wird pausiert...')

        if (query_data == "cmd_back"):
            self.bot.answerCallbackQuery(query_id, text='Kommando noch nicht implementiert')

        if (query_data == "cmd_skip"):
            if (not self.config["allow_skip"] and not from_id in self.admins):
                self.bot.answerCallbackQuery(query_id, text='Die Skip-Funktion wurde deaktiviert!')
            else:
                self.pbm.skip(1)
                self.bot.answerCallbackQuery(query_id, text='Springe zum nächsten Lied...')
                time.sleep(0.1)
                try:
                    self.bot.editMessageText((from_id, message_id), 
                        self.controller_message(), reply_markup=self.controller_keyboard())
                except telepot.exception.TelegramError:
                    pass

        if (query_data == "cmd_vol+"):
            self.pbm.increase_volume()
            self.bot.answerCallbackQuery(query_id, text=self.pbm.print_volume())
        if (query_data == "cmd_vol-"):
            self.pbm.decrease_volume()
            self.bot.answerCallbackQuery(query_id, text=self.pbm.print_volume())
        if (query_data == "cmd_like"):
            self.bot.answerCallbackQuery(query_id, text='Danke für dein Feedback!')
        if (query_data == "cmd_dislike"):
            self.bot.answerCallbackQuery(query_id, text='Danke für dein Feedback!')

    def handle_textmessage(self, msg, chat_id):
        """Wird aufgerufen, wenn eine Textnachricht empfangen wurde.
        Die Liste der Kommandos sollte über den BotFather angepasst werden.
        """

        message = msg["text"]
        logging.info("Neue Nachricht von " + msg["from"]["first_name"] + " (" + str(chat_id) + "): " + message)

        # /ip: Gibt die IP des Pi aus
        if (message == "/ip"):
            self.bot.sendMessage(chat_id, self.get_ip())

        # /admin: Admin-Modus
        if (message[:6] == "/admin"):
            if (len(message) > 7):
                if (message[7:] == self.config["admin_pw"]):
                    if (chat_id in self.admins):
                        self.bot.sendMessage(chat_id, "Dude, du bist längst Admin")
                        return
                    self.admins.append(chat_id)
                    f = open(Soutibot.adminsfile, "w")
                    json.dump(Soutibot.admins, f)
                    f.close()
                    self.bot.sendMessage(chat_id, "Yaaay, jetzt bist du Admin")
                else:
                    self.bot.sendMessage(chat_id, "Falsches Passwort, aber netter Versuch.")
            else:
                if (chat_id in self.admins):
                    self.bot.sendMessage(chat_id, "Du gehörst bereits zur allmächtigen Eliteeinheit der Admins!")
                else:
                    self.bot.sendMessage(chat_id, "Du bist kein Admin! Für den Admin-Modus: /admin <passwort>")

        if (message[:7] == "/config"):
            if (not chat_id in self.admins):
                self.bot.sendMessage(chat_id, "Du bist kein Admin. Finger weg von der Config!")
                return
            if (len(message) > 8):
                tokens = message.split(" ")
                if (len(tokens) != 3):
                    self.bot.sendMessage(chat_id, "Hä? Benutze /config <option> <wert> um die Config zu ändern.")
                    return
                option = tokens[1]
                value = tokens[2]
                if (option in self.config):
                    if (value.lower() == "true"):
                        self.config[option] = True
                    elif (value.lower() == "false"):
                        self.config[option] = False
                    elif (value.isdigit()):
                        self.config[option] = int(value)
                    else:
                        self.config[option] = value
                    f = open(Soutibot.configfile, "w")
                    json.dump(Soutibot.config, f)
                    f.close()
                    self.bot.sendMessage(chat_id, "Config geändert.")
                else:
                    self.bot.sendMessage(chat_id, "Sorry, das ist keine Option.")
            else:
                self.bot.sendMessage(chat_id, self.config)


        # /vol: Gibt die Lautstärke aus; /vol n setzt die Lautstärke auf n
        if (message[:4] == "/vol"):
            if (len(message) > 5):
                try:
                    number = int(message[5:])
                    if ((number < 0) or (number > 100)):
                        self.bot.sendMessage(chat_id, "Fehler: Bitte gib nach /vol eine Zahl zwischen 1 und 100 ein, um die Lautstärke zu ändern!")
                    else:
                        self.pbm.set_volume(number)
                except ValueError:
                    self.bot.sendMessage(chat_id, "Fehler: Bitte gib nach /vol eine Zahl zwischen 1 und 100 ein, um die Lautstärke zu ändern!")
            else:
                self.bot.sendMessage(chat_id, self.pbm.print_volume())

        # /skip: Springt zum nächsten Lied; /skip n überspringt n Tracks
        if (message[:5] == "/skip"):
            if (not self.config["allow_skip"] and not chat_id in self.admins):
                self.bot.sendMessage(chat_id, "Skip wurde deaktiviert!")
                return
            if (len(message) > 6):
                try:
                    number = int(message[6:])
                    self.pbm.skip(number)
                except ValueError:
                    self.bot.sendMessage(chat_id, "Fehler: Bitte gib nach /skip eine Zahl ein, um mehrere Tracks zu überspringen!")
            else:
                self.pbm.skip(1)

        # /play: Gibt die aktuelle Wiedergabe mit Buttons zur Steuerung aus;
        # /play x durchsucht die Musiksammlung nach x und spielt das Ergebnis;
        # /play random x mischt die Ergebnisse zufällig durch
        if (message[:5] == "/play"):
            if (len(message) == 5):
                self.bot.sendMessage(chat_id, self.controller_message(), reply_markup=self.controller_keyboard())
                return
            if (message[6:12].lower() == "random"):
                self.pbm.query(message[13:], True)
            else:
                self.pbm.query(message[6:], False)

        if (message[:5] == "/list"):
            playlist = self.pbm.print_queue()
            if (playlist == ""):
                playlist = "Die Playlist ist leer!"
            self.bot.sendMessage(chat_id, playlist)

        # YouTube-Links werden in einer eigenen Methode behandelt
        if ("youtube" in message):
            self.handle_youtube(message, chat_id)
                
    def handle_audiofile(self, audio, chat_id):
        """Wird aufgerufen, wenn eine Audiodatei empfangen wurde. Diese
        wird über den DownloadManager heruntergeladen.
        """

        # Falls die Datei Titel und/oder Interpret enthält, wird sie
        # dementsprechend benannt bzw. eingeordnet
        if ("performer" in audio):
            artist = audio["performer"]
        else:
            artist = "unbekannt"
        if ("title" in audio):
            title = audio["title"]
        else:
            title = "unbekannt-" + str(random.randint(0,10000000))
        
        logging.debug("Empfange Audiodatei von " + str(chat_id) + ":\n" + artist + " - " + title)
        
        file_id = audio["file_id"]
        saveloc = self.muckedir + "/unsortiert/" + artist # TODO: Genre
        self.dlm.query((file_id, saveloc, title))
        
    def handle_youtube(self, message, chat_id):
        """Wird aufgerufen, wenn ein YouTube-Link empfangen wurde. Die Tonspur
        des Videos wird automatisch heruntergeladen und abgespielt.
        """

        # TODO: Bessere Erkennung von Links, besseres Exception-Handling
        try:
            video = pafy.new(message)
            self.bot.sendMessage(chat_id, "Lade Video von Youtube: " + video.title)
            saveloc = self.muckedir + "/unsortiert/youtube/"
            self.dlm.query_youtube((video, saveloc, chat_id))
        except OSError:
            logging.error("OSError beim YT-DL: " + message)
        except ValueError:
            self.bot.sendMessage(chat_id, "Der Techniker ist informiert.")
            logging.error("ValueError beim YT-DL: " + message)

    def controller_message(self):
        """Gibt die Nachricht zurück, die bei Aufruf von /play ausgegeben wird.
        """

        message = ""

        # Aktuelle Wiedergabe:
        if (self.pbm.current_track() == ""):
            message += "Aktuell läuft keine Musik.\n"
        else:
            next_tracks = self.pbm.print_queue().split("\n")
            message += "Aktuell läuft:\n" + next_tracks[0] + "\n"
            del(next_tracks[0])
            del(next_tracks[len(next_tracks)-1])
            # Nächste Titel der Warteschlange:
            if (len(next_tracks) == 0):
                message += "Danach ist keine Musik mehr eingereiht.\n"
            elif (len(next_tracks) < 6):
                message += "\nAls nächstes folgt:\n"
                for track in next_tracks:
                    message += track + "\n"
            else:
                # Ab mehr als fünf Tracks wird die Nachricht abgekürzt:
                message += "\nAls nächstes folgt:\n"
                for i in range(4):
                    message += next_tracks[i] + "\n"
                message += "(..." + str(len(next_tracks)-4) + " weitere Titel)"

        return message

    def controller_keyboard(self):
        """Generiert die Tastatur, die zur Steuerung verwendet wird.
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Aktualisieren \U0001F501', callback_data='cmd_refresh'),
                InlineKeyboardButton(text='Play/Pause  \U000023EF', callback_data='cmd_playpause')],
                [InlineKeyboardButton(text='Zurück \U000023EE', callback_data='cmd_back'),
                InlineKeyboardButton(text='Skip \U000023ED', callback_data='cmd_skip')],
                [InlineKeyboardButton(text='Volume- \U0001F509', callback_data='cmd_vol-'),
                InlineKeyboardButton(text='Volume+ \U0001F50A', callback_data='cmd_vol+')],
                #[InlineKeyboardButton(text="Nich so gut! \U0001F44E", callback_data='cmd_dislike'),
                #    InlineKeyboardButton(text="Geiler Scheiß! \U0001F44D", callback_data='cmd_like')],
                ])

        return keyboard
        
    def start(self):
        """Initiiert den message_loop von Telepot und wartet so auf Nachrichten.
        Blockiert, bis running auf False gesetzt wird.
        """

        self.running = True
        self.bot.message_loop({'chat': self.on_chat_message,
                    'callback_query': self.on_callback_query})

        while (self.running):
            if (not self.dlm.running):
                self.dlm.start()
            time.sleep(10)

    def shutdown(self):
        """Beendet die anderen Threads und schließlich den Bot an sich.
        """

        logging.info("Das war's")

        self.dlm.stop()
        self.pbm.stop()
        self.running = False
