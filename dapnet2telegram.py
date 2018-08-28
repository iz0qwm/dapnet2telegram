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
import ast
import json
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram import Location
from telegram.error import BadRequest
from pprint import pprint
import subprocess
from emoji import emojize

version = subprocess.check_output(["git", "describe"]).strip()

# Leggo il file di configurazione
cfg = configparser.RawConfigParser()
try:
    # attempt to read the config file winlinktodapnet.cfg
    config_file = os.path.join(os.path.dirname(__file__), 'dapnet2telegram.cfg')
    cfg.read(config_file)
except:
    # no luck reading the config file, write error and bail out
    print(os.path.basename(__file__) + " could not find / read config file")
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

# Leggo il file di presenza per aprs
aprspresencefile = cfg.get('aprsis','presencefile')

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
    bot.send_message(chat_id=update.message.chat_id, text="*Software version*: " + version + "\r\n*Author*: Raffaello IZ0QWM\r\n*Server connection*: " + hampagerurl + "\r\n*Github*: [dapnet2telegram](https://github.com/iz0qwm/dapnet2telegram)", parse_mode='Markdown', disable_web_page_preview=True)

about_handler = CommandHandler('about', about)
dispatcher.add_handler(about_handler)

# Comando help
def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Puoi darmi i seguenti comandi:\r\n*/help* per i comandi\r\n------\r\n*/about* informazioni e versione\r\n------\r\n*/check CALLSIGN* - per controllare se il CALLSIGN e' registrato su DAPNET\r\n------\r\n*/send FROM TO TRGROUP Messaggio* - per inviare un messaggio:\r\n*FROM:* e' il tuo nominativo\r\n*TO:* il nominativo del destinatario\r\n*TRGROUP:* il transmitter group\r\n------\r\n*/calls N* - la lista degli ultimi N messaggi inviati (max. 10)\r\n------\r\n*/trgroups* - per la lista dei transmitters groups\r\n------\r\n*/trx CALL* - per richiedere info sullo stato di un transmitter\r\n------\r\n*/aprs* - per la lista degli user raggiungibili via APRS", parse_mode='Markdown')

help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

# Comando send
def send(bot, update, args):
    # Invio messaggio -> DAPNET
    if len(args) < 4:
        output = ":warning: Devi inserire tutti i campi:\r\n*/send FROM TO TRGROUP Messaggio*"
        output = emojize(output)
        bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')
    else:
        # Create the complete URL to send to DAPNET
        http = urllib3.PoolManager()
        headers = urllib3.util.make_headers(basic_auth= hampagerusername + ':' + hampagerpassword)
        da = str(args[0]).lower()
        to = str(args[1]).lower()
        trgroup = str(args[2]).lower()
        messaggio = " ".join(args[3:])
        payload = '{ "text": "'+ da +': ' + messaggio +'", "callSignNames": [ "' + to + '" ], "transmitterGroupNames": [ "' + trgroup +'" ], "emergency": false}'
        logger.info('Payload: %s', payload)

        try:
            # Try to establish connection to DAPNET
            response = requests.post(hampagerurl, headers=headers, data=payload)
        except:
            # Connection to DAPNET failed, write warning to console, write warning to error log then bail out
            logger.error('Invalid DAPNET credentials or payload not well done')
            sys.exit(0)
        else:
            # Connection to DAPNET has been established, continue
            logger.info('-------------------------------------------')
            logger.info('MESSAGGIO INVIATO SU DAPNET')
            logger.info('-------------------------------------------')
	    text_invio = "Messaggio inviato su DAPNET a " + to + " da " + da
            bot.send_message(chat_id=update.message.chat_id, text=text_invio)

send_handler = CommandHandler('send', send, pass_args=True)
dispatcher.add_handler(send_handler)

# Comando check - Controllo nominativi
def check(bot, update, args):
    if len(args) < 1:
        output = ":warning: Devi inserire tutti i campi:\r\n*/check CALLSIGN*"
        output = emojize(output)
        bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')
    else:
        callsign = str(args[0]).strip().lower()
        # Controllo prima se esiste nel file
        if callsign in open(statefile).read():
          # Se esiste controllo il json
          with open(statefile, 'r') as data_file:    
              data = json.load(data_file)
          # Se esiste tra i callsigns
          if callsign in data["callSigns"]:
              ric = str(data["callSigns"][callsign]["pagers"][0]["number"])
              nome = str(data["callSigns"][callsign]["description"])
              output = "*Call:* " + callsign + " - *Nome:* " + nome + " - *RIC:* " + ric
          else:
              output = "Mi dispiace, " + callsign + " non e' registrato come user" 
        else: 
          output = "Mi dispiace, " + callsign + " non e' registrato."

	output = emojize(output)
        bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')

check_handler = CommandHandler('check', check, pass_args=True)
dispatcher.add_handler(check_handler)

# Comando trx - Controllo stato transmitters
def trx(bot, update, args):
    if len(args) < 1:
        output = ":warning: Devi inserire tutti i campi:\r\n*/trx CALL*"
        output = emojize(output)
        bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')
    else:
        callsign_argomento = str(args[0])
        callsign = callsign_argomento.lower()
        # Controllo prima se esiste nel file
        if callsign in open(statefile).read():
          # Se esiste controllo il json
          with open(statefile, 'r') as data_file:
              data = json.load(data_file)
          if callsign in data["transmitters"]:
            status = str(data["transmitters"][callsign]["status"])
            nome = str(data["transmitters"][callsign]["name"])
            timeslot = str(data["transmitters"][callsign]["timeSlot"])
            latitudine = float(data["transmitters"][callsign]["latitude"])
            longitudine = float(data["transmitters"][callsign]["longitude"])
            output = "*Call:* " + nome + " - *Stato:* " + status + " - *timeslot:* " + timeslot + "\r\n*Location:*"
          else:
            output = "Mi dispiace, " + callsign + " non e' registrato come transmitter"

        else:
          output = "Mi dispiace, " + callsign + " non e' registrato."

        bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')
        bot.send_location(chat_id=update.message.chat_id, latitude=latitudine, longitude=longitudine, live_period=80)

trx_handler = CommandHandler('trx', trx, pass_args=True)
dispatcher.add_handler(trx_handler)

# Comando calls (messaggi)
def calls(bot, update, args):
    if len(args) < 1:
        output = "Non hai inserito alcun valore, ti presento gli ultimi 3 messaggi:\r\n"
        output = emojize(output)
        bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')
        scelta = 3
    else:
        scelta = int(args[0])

    if scelta > 10:
        scelta = 10
    if scelta < 1 :
        scelta = 1
    # Leggiamo il file State.json
    with open(statefile, 'r') as data_file:
        data = json.load(data_file)

    lunghezza = len(data["calls"])

    output = ""
    for i in range(lunghezza - scelta, lunghezza): 
        testo = str(data["calls"][i]["text"])
        orario = str(data["calls"][i]["timestamp"])
        giorno,ora_completa = orario.split("T")
        ora,escluso = ora_completa.split(".")
        # Uso json.dumps per rimuovere le u di Unicode
        mittente = json.dumps(data["calls"][i]["callSignNames"])
        trgroup = json.dumps(data["calls"][i]["transmitterGroupNames"])

        output = output + ":pager: " + giorno + " " + ora + " - *TO:* " + mittente.replace(r'"','') + " - *TRGROUP:* " + trgroup.replace(r'"','') + "\r\n" + "*FROM:* " + testo + "\r\n\r\n"
     
    output = emojize(output)
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
        nome = str(data["transmitterGroups"][i]["name"])
        descrizione = str(data["transmitterGroups"][i]["description"])
        # Uso json.dumps per rimuovere le u di Unicode
        trx = json.dumps(data["transmitterGroups"][i]["transmitterNames"])
        output = output + "*Nome:* " + nome + " - *Descr.:*" + descrizione + " - *TRX:*" + trx.replace(r'"','') + "\r\n\r\n"

    bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')

trgroups_handler = CommandHandler('trgroups', trgroups)
dispatcher.add_handler(trgroups_handler)

# Comando aprs (Controllo utenti raggiungibili via aprs)
def aprs(bot, update):

    output = ""
    presencefile = open(aprspresencefile, 'r')
    with presencefile as file:
       file.seek(0) #sono all'inzion del file
       primo_carattere = file.read(1) # Prendo il primo carattere
       if not primo_carattere:
          output = "Nessun user DAPNET presente su APRS"
       else:
          file.seek(0) # ritorno all'inizio del file
          for line in presencefile:
               call = line
               output = output + line

    bot.send_message(chat_id=update.message.chat_id, text="Elenco degli user DAPNET che possono ricevere messaggi anche via APRS.\r\n*ATTENZIONE*: inviare i messaggi ai CALL senza il SSID (Es. IZ0QWM-9 va inviato a IZ0QWM)\r\nPer informazioni su come funziona il gateway *DAPNET <-> APRS* visitare:\r\n*Github*: [dapaprsgate](https://github.com/iz0qwm/dapaprsgate)", parse_mode='Markdown', disable_web_page_preview=True)
    bot.send_message(chat_id=update.message.chat_id, text=output, parse_mode='Markdown')

aprs_handler = CommandHandler('aprs', aprs)
dispatcher.add_handler(aprs_handler)

# Comando Unknown
def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Mi dispiace, non ho capito il comando.\r\nSe non li ricordi, digita /help")

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

# Lo faccio partire
#updater.idle()
updater.start_polling()
#updater.stop()
