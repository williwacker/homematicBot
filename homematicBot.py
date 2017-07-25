# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Homematic and Pilight bot
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram
import logging
import configparser
import urllib3
import certifi
import xmltodict
import os
import re

class homematicBot(object):

	def __init__(self):
		# Enable logging
		if os.name == "posix":
			logfile = "/var/log/"+os.path.splitext(os.path.basename(__file__))[0]+".log"
		else:
			logfile = ""
		logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
								filename=logfile,level=logging.INFO)
		self.logger = logging.getLogger(__name__)

		self.http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())
		fname = os.path.splitext(os.path.abspath(__file__))[0]+'.ini'
		if os.path.isfile(fname):
			self.prefs = self.__read_configuration__(fname)
		else:
			logging.warn('{} not found'.format(fname),True)
			exit(1)

	def __read_configuration__(self,filename): #read configuration from the configuration file and prepare a preferences dict
		cfg = configparser.ConfigParser()
		cfg.read(filename)
		preferences = {}
		for sectionname, section in cfg.items():
			preferences[sectionname] = {}
			for name, value in cfg.items(sectionname):
				preferences[sectionname][name] = value
		return preferences

	# Write SysVar in Homematic Server
	def write_SysVar(self,name,sysvalue):
		trans_url = {'Ü':'%DC','ü':'%FC','Ö':'%D6','ö':'%F6','Ä':'%C4','ä':'%E4',' ':'%20'}
		for key, value in trans_url.items():
			sysvalue = sysvalue.replace(key,value)
		response = self.http.request('GET','http://192.168.178.11:8181/x.exe?state=dom.GetObject("'+name+'").State("'+sysvalue+'")')

	# Read SysVar from Homematic Server
	def read_SysVar(self,name):
		response = self.http.request('GET','http://192.168.178.11:8181/x.exe?state=dom.GetObject("'+name+'").Value()')
		return re.search(b'.*<state>(.*?)</state>.*$',response.data).group(1).decode('iso-8859-1')

	# Turn on or off switches via Pilight service
	def pilight(self,device,state):
		self.http.request('GET','http://192.168.178.12:5001/send?{"action":"control","code":{"device":"'+device+'","state":"'+state+'"}}')

	# Define a few command handlers. These usually take the two arguments bot and
	# update. Error handlers also receive the raised TelegramError object in error.
	def einschalten(self,bot,update):
		if self.check_user(update):
			command = update.message.text.split()
			if len(command) > 1:
				if command[1].lower() in self.prefs['SCHALTER']:
					schalter = self.prefs['SCHALTER'][command[1].lower()]
					self.pilight(schalter,'on')
					update.message.reply_text('{} eingeschaltet'.format(schalter))
				else:
					update.message.reply_text('{} nicht bekannt'.format(command[1]))
			else:
				update.message.reply_text('kein Schaltername angegeben')

	def ausschalten(self,bot,update):
		if self.check_user(update):
			command = update.message.text.split()
			if len(command) > 1:
				if command[1].lower() in self.prefs['SCHALTER']:
					schalter = self.prefs['SCHALTER'][command[1].lower()]
					self.pilight(schalter,'off')
					update.message.reply_text('{} ausgeschaltet'.format(schalter))
				else:
					update.message.reply_text('{} nicht bekannt'.format(command[1]))
			else:
				update.message.reply_text('kein Schaltername angegeben')

	def hmget(self,bot,update):
		if self.check_user(update):
			command = update.message.text.split()
			if len(command) > 1:
				if command[1].lower() in self.prefs['HOMEMATIC']:
					item = self.prefs['HOMEMATIC'][command[1].lower()]
					value = self.read_SysVar(item)
					update.message.reply_text('{} = {}'.format(item,value))
				else:
					update.message.reply_text('{} nicht bekannt'.format(command[1]))
			else:
				update.message.reply_text('keinen Parameter angegeben')

	def hmset(self,bot,update):
		if self.check_user(update):
			command = update.message.text.split()
			if len(command) > 2:
				if command[1].lower() in self.prefs['HOMEMATIC-SET']:
					items = self.prefs['HOMEMATIC-SET'][command[1].lower()].split(':')
					if command[2] in items[1:]:
						value = self.write_SysVar(items[0],command[2])
						update.message.reply_text('{} = {}'.format(items[0],command[2]))
					else:
						update.message.reply_text('ungültiger Parameter für {} {}!'.format(items[0],command[2]))
				else:
					update.message.reply_text('{} nicht bekannt!'.format(command[1]))
			else:
				update.message.reply_text('zu wenig Parameter angegeben!')


	def help(self,bot,update):
		print('in help')
		if self.check_user(update):
			helpText = ['<b>Hier die gültigen Befehle:</b>']
			helpText.append('<i>Schalter:</i>')
			for name in self.prefs['SCHALTER']:
				helpText.append('/an {0}\n/aus {0}'.format(name))
			helpText.append('<i>Homematic:</i>')
			for name in self.prefs['HOMEMATIC']:
				helpText.append('/hmget {0}'.format(name))
			for name in self.prefs['HOMEMATIC-SET']:
				values = name.split(':')
				helpText.append('/hmset {0} {1}'.format(name,"|".join(values[1:])))
			bot.sendMessage(chat_id=update.message.chat_id,text='\n'.join(helpText),parse_mode=telegram.ParseMode.HTML)

	def echo(self,bot,update):
		update.message.reply_text(update.message.text)


	def error(self,bot,update, error):
		self.logger.warn('Update "%s" caused error "%s"' % (update, error))

	def start(self,bot,update):
		# Your bot will send this message when users first talk to it, or when they use the /start command
		if self.check_user(update):
			update.message.reply_text('Hi {}. Welcome to my Homematic Bot.'.format(update.message.chat['first_name']))

	def check_user(self,update):
		if update.message.chat['username'] in self.prefs['USERS']['allowedusers']:
			return True
		else:
			update.message.reply_text('Hi {}. I don\'t know you'.format(update.message.chat['username']))
			return False


	def startBot(self):
		# Create the EventHandler and pass it your bot's token.
		updater = Updater(self.prefs['TOKEN']['homematic'])

		# Get the dispatcher to register handlers
		dp = updater.dispatcher

		# on different commands - answer in Telegram
		dp.add_handler(CommandHandler("an", self.einschalten))
		dp.add_handler(CommandHandler("aus", self.ausschalten))
		dp.add_handler(CommandHandler("hmget", self.hmget))
		dp.add_handler(CommandHandler("hmset", self.hmset))
		dp.add_handler(CommandHandler("help", self.help))
		dp.add_handler(CommandHandler("start", self.start))

		# on noncommand i.e message - echo the message on Telegram
		dp.add_handler(MessageHandler(Filters.text, self.echo))

		# log all errors
		dp.add_error_handler(self.error)

		# Start the Bot
		updater.start_polling()

		# Run the bot until the you presses Ctrl-C or the process receives SIGINT,
		# SIGTERM or SIGABRT. This should be used most of the time, since
		# start_polling() is non-blocking and will stop the bot gracefully.
		updater.idle()


if __name__ == '__main__':
	HM = homematicBot()
	HM.startBot()
