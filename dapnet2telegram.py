#!/usr/bin/env python
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Author: Raffaello Di Martino IZ0QWM
# Date: 18.08.2018
# Version 0.1

import logging
import urllib2
import urllib3
import time
from time import sleep
from datetime import datetime
import sys
import configparser
import os
import requests
import string
import requests
import websocket
import string
import json
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from pprint import pprint

# Leggo il file di configurazione
cfg = configparser.RawConfigParser()
try:
    # attempt to read the config file winlinktodapnet.cfg
    config_file = os.path.join(os.path.dirname(__file__), 'dapnet2telegram.cfg')
    cfg.read(config_file)
except:
    # no luck reading the config file, write error and bail out
    logger.error('winlinktodapnet could not find / read config file')
    sys.exit(0)

# Leggo la posizione del logfile
logfile = cfg.get('misc', 'logfile')

# Leggo le credenziali per DAPNET
hampagerusername = cfg.get('dapnet','user')
hampagerpassword = cfg.get('dapnet','password')
hampagerurl = cfg.get('dapnet','baseurl') + cfg.get('dapnet','coreurl')
statefile = cfg.get('dapnet','statefile')

# Leggo il token per Telegram
telegramtoken = cfg.get('telegram','token')

# logging.basicConfig(filename='winlinktodapnet.log',level=logging.INFO) # level=10
logger = logging.getLogger('dapnet2telegram')
handler = logging.FileHandler(logfile)
logformat = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(logformat)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

updater = Updater(token=telegramtoken)
dispatcher = updater.dispatcher

# Comando di start
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Ciao, sono il *bot di DAPNET Italia*. Digita /help per i comandi", parse_mode='Markdown')

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# Comando di About
def about(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="*Software version*: 1.2.0\r\n*Author*: Raffaello IZ0QWM\r\n", parse_mode='Markdown')

about_handler = CommandHandler('about', about)
dispatcher.add_handler(about_handler)

# Comando help
def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Puoi darmi i seguenti comandi:\r\n*/help* per i comandi\r\n------\r\n*/check CALLSIGN* - per controllare se il CALLSIGN e' registrato su DAPNET\r\n------\r\n*/send FROM TO TRGROUP Messaggio* - per inviare un messaggio:\r\n*FROM:* e' il tuo nominativo\r\n*TO:* il nominativo del destinatario\r\n*TRGROUP:* il transmitter group\r\n------\r\n*/calls N* - la lista degli ultimi N messaggi inviati (max. 10)\r\n------\r\n*/trgroups* - per la lista dei transmitters groups\r\n------\r\n", parse_mode='Markdown')

help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

# Comando send
def send(bot, update, args):
    # Invio messaggio -> DAPNET
    #create the complete URL to send to DAPNET
    http = urllib3.PoolManager()
    headers = urllib3.util.make_headers(basic_auth= hampagerusername + ':' + hampagerpassword)
    da = str(args[0]).lower()
    to = str(args[1]).lower()
    trgroup = str(args[2]).lower()
    messaggio = " ".join(args[3:])
    payload = '{ "text": "'+ da +': ' + messaggio +'", "callSignNames": [ "' + to + '" ], "transmitterGroupNames": [ "' + trgroup +'" ], "emergency": false}'
    logger.info('Payload: %s', payload)
    #print(headers)
    #print(payload)

    try:
        #try to establish connection to DAPNET
        response = requests.post(hampagerurl, headers=headers, data=payload)
    except:
        #connection to DAPNET failed, write warning to console, write warning to error log then bail out
        logger.error('Invalid DAPNET credentials or payload not well done')
        sys.exit(0)
    else:
        #connection to DAPNET has been established, continue
        logger.info('-------------------------------------------')
        logger.info('MESSAGGIO INVIATO SU DAPNET')
        logger.info('-------------------------------------------')
	text_invio = "Messaggio inviato su DAPNET a " + to + " da " + da
        bot.send_message(chat_id=update.message.chat_id, text=text_invio)

send_handler = CommandHandler('send', send, pass_args=True)
dispatcher.add_handler(send_handler)

# Comando check
def check(bot, update, args):
    callsign_argomento = str(args[0])
    callsign = callsign_argomento.lower()
    # Controllo prima se esiste nel file
    if callsign in open(statefile).read():
      # Se esiste controllo il json
      with open(statefile, 'r') as data_file:    
          data = json.load(data_file)
      ric = str(data["callSigns"][callsign]["pagers"][0]["number"])
      nome = str(data["callSigns"][callsign]["description"])
      output = "*Call:* " + callsign + " - *Nome:* " + nome + " - *RIC:* " + ric
    else: 
      output = "Mi dispiace, " + callsign + " non e' registrato."

    bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')

check_handler = CommandHandler('check', check, pass_args=True)
dispatcher.add_handler(check_handler)

# Comando calls (messaggi)
def calls(bot, update, args):
    scelta = int(args[0])

    if scelta > 10:
	scelta = 10
    if scelta == 0:
        scelta = 1
    # Leggiamo il file State.json
    with open(statefile, 'r') as data_file:
        data = json.load(data_file)

    lunghezza = len(data["calls"])

    output = ""
    for i in range(lunghezza-scelta, lunghezza): 
        testo = str(data["calls"][i]["text"])
        orario = str(data["calls"][i]["timestamp"])
        giorno,ora_completa = orario.split("T")
        ora,escluso = ora_completa.split(".")
        mittente = str(data["calls"][i]["callSignNames"])
        trgroup = str(data["calls"][i]["transmitterGroupNames"])

        output = output + "*-*" + giorno + " " + ora + " - *TO:*" + mittente + " - *FROM:*" + testo + " - *TRGROUP:*" + trgroup + "\r\n"

    bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')

calls_handler = CommandHandler('calls', calls, pass_args=True)
dispatcher.add_handler(calls_handler)

# Comando trgroups (Transmitters groups)
def trgroups(bot, update):

    # Leggiamo il file State.json
    with open(statefile, 'r') as data_file:
        data = json.load(data_file)
    
    output = ""
    for i in data["transmitterGroups"]: 
        #print(str(i)) 
        #pprint(data["transmitterGroups"]["pocgat"]["name"])
        nome = str(data["transmitterGroups"][i]["name"])
        descrizione = str(data["transmitterGroups"][i]["description"])
        trx = str(data["transmitterGroups"][i]["transmitterNames"])
        output = output + "*Nome:* " + nome + " - *Descr.:*" + descrizione + " - *TRX:*" + trx + "\r\n\r\n"

    bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')

trgroups_handler = CommandHandler('trgroups', trgroups)
dispatcher.add_handler(trgroups_handler)

# Comando Unknown
def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Mi dispiace, non ho capito il comando.\r\nSe non li ricordi, digita /help")

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

# Lo faccio partire
#updater.idle()
updater.start_polling()
#updater.stop()
