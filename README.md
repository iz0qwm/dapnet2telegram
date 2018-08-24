# Telegram Bot for DAPNET Italia
## dapnet2telegram

Semplice Bot che:
* Permette di verificare se un call è stato registrato su DAPNET
* Permette di inviare un messaggio via DAPNET
* Lista gli ultimi N messaggi inviati su DAPNET
* Lista i gruppi di transmitters
* Permette di vedere lo stato di un transmitter
* Lista gli user DAPNET raggiungibili via APRS

## Come funziona
E' necessario che il Bot risieda sulla stessa macchina dove c'è
il Core di DAPNET.  
Creare un Bot su Telegram e copiare il TOKEN.  
Compilare il _.cfg_ con le proprie _credenziali amministrative_ di DAPNET e con il TOKEN
per Telegram Bot.  
Se si vuole far funzionare anche la voce di menu */aprs* è necessario che sia presente
anche il **dapaprsgate**: https://github.com/iz0qwm/dapaprsgate

## Elenco dei comandi disponibili

**/help** per i comandi  

**/about** informazioni e versione  

**/check CALLSIGN** - per controllare se il CALLSIGN e' registrato su DAPNET  

**/send FROM TO TRGROUP Messaggio** - per inviare un messaggio:  
FROM: e' il tuo nominativo  
TO: il nominativo del destinatario  
TRGROUP: il transmitter group  

**/calls N** - la lista degli ultimi N messaggi inviati (max. 10)  

**/trgroups** - per la lista dei transmitters groups  

**/trx CALL** - per richiedere info sullo stato di un transmitter

**/aprs** - per la lista degli user raggiungibili via APRS

