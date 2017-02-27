# downloadmgr.py
# Stellt eine Klasse zur Verfügung, die der Soutibot zur Verwaltung von
# Downloads benutzt. Audiodateien und YouTube-Links können eingereiht werden
# und werden nacheinander in einem eigenen Thread heruntergeladen.
#
# Letztes Update: 16.01.2017 (Code kommentiert)

# Um zu überprüfen, ob ein Verzeichnis existiert und es ggfs. anzulegen
import os

# Damit die Downloads in einem eigenen Thread laufen können
from threading import Thread

# Falls gerade nichts zu tun ist, damit der Thread schlafen kann
import time

import logging

# Siehe soutibot.py; zum Download von YouTube-Videos
import pafy

# Die anderen Klassen brauchen wir natürlich auch:
import soutibot
import playbackmgr

class DownloadManager():
    """Der DownloadManager. Managt Downloads.
    """

    running = False # Läuft beim DownloadManager?
    SLEEPTIME = 0.1 # Für gesunden Sekundenschlaf zwischendurch
    download_queue = [] # Warteschlange für Dateien
    youtube_queue = [] # Warteschlange für YouTube

    @staticmethod
    def start():
        """Initialisiert den DownloadManager und spawnt einen separaten Thread
        """

        queue_thread = Thread(target=DownloadManager.process_queue)
        DownloadManager.running = True
        logging.info("DownloadManager loift!")
        queue_thread.start()

    @staticmethod
    def query(request):
        """Reiht eine Datei in die Download-Warteschlange ein
        """

        DownloadManager.download_queue.append(request)

    @staticmethod
    def query_youtube(request):
        """Reiht ein YouTube-Video in die entsprechende Warteschlange ein
        """

        DownloadManager.youtube_queue.append(request)

    @staticmethod
    def process_queue():
        """Arbeitet nacheinander beide Warteschlangen ab, bis running
        auf False gesetzt wird.
        """

        while (DownloadManager.running):
            if (len(DownloadManager.download_queue) > 0):
                request = DownloadManager.download_queue[0]
                del DownloadManager.download_queue[0]
                file_id = request[0]
                path = request[1]
                title = request[2]
                DownloadManager.download_file(file_id, path, title)
            if (len(DownloadManager.youtube_queue) > 0):
                request = DownloadManager.youtube_queue[0]
                del DownloadManager.youtube_queue[0]
                video = request[0]
                path = request[1]
                chat_id = request[2]
                DownloadManager.download_youtube(video, path, chat_id)
            time.sleep(DownloadManager.SLEEPTIME)

    @staticmethod
    def stop():
        """Beendet die Schleife nach dem aktuellen Durchgang und stoppt so
        den Download-Thread.
        """
        logging.info("DownloadManager wird gestoppt.")
        DownloadManager.running = False

    @staticmethod
    def download_file(file_id, path, title):
        """Lädt eine per Telegram empfangene Datei herunter und speichert sie
        """

        bot = soutibot.Soutibot.bot
        if not os.path.exists(path):
            os.makedirs(path)
        ending = bot.getFile(file_id)["file_path"].split('.')[1]
        bot.download_file(file_id, path + '/' + title + '.' + ending)
        logging.info("Datei wurde runtergeladen!")

    @staticmethod
    def download_youtube(video, path, chat_id):
        """Lädt den besten verfügbaren m4a-Stream des Videos herunter,
        speichert die Datei und reiht sie in die Wiedergabeliste ein
        """

        pbm = playbackmgr.PlaybackManager
        current_queue = pbm.print_queue()
        playbackmgr.PlaybackManager.query(video.title, False)
        if (not current_queue == pbm.print_queue()):
            return
        
        bot = soutibot.Soutibot.bot
        bestaudio = video.getbestaudio(preftype="m4a", ftypestrict=True)
        try:
            bestaudio.download(filepath=path, quiet=False)
            bot.sendMessage(chat_id, "Video wurde runtergeladen und eingereiht!")
            playbackmgr.PlaybackManager.query(video.title, False)
        except OSError:
            bot.sendMessage(chat_id, "Dieses Video kann nicht runtergeladen werden... Der Techniker ist informiert!")
            logging.error("Video kann nicht geladen werden:" + video.title)

class YTLibrary():

    dbfile = ""
    library = []

    def __init__(self, directory):
        self.dbfile = directory + "/youtube.db"
        if (not os.path.isfile(self.dbfile)):
            f = open(self.dbfile, "w")
            json.dump(self.library, f)
            f.close()
        else:
            f = open(self.dbfile)
            self.library = json.load(f)
            f.close()

    def add_video(self, video, username):
        valid_title = video.title.translate({ord(c): None for c in '.,/\\:\"\'!#$@'})
        new_entry = {"original_title": video.title, "video_id": video.videoid,
                        "valid_title": valid_tile, "sender": username}
        self.library.append(new_entry)
        f = open(self.dbfile, "w")
        json.dump(self.library, f)
        f.close()
