__author__ = 'Palli'

import sys
import socket
import time
import Queue
import thread
from threading import Timer

class IrcClient:

    def __init__(self):
        self.host = sys.argv[1]
        self.irc_sever = socket.socket()
        self.irc_sever.connect((self.host, 6667))
        self.nickname = 'defaultNick'
        self.username = 'defaultUsername'
        self.server = 'defaultServer'
        self.realname = 'default real name'
        self.buffer = ''
        self.message_queue = Queue.Queue()
        self.log_file = open('irc.log', 'a')
    def __del__(self):
        self.log_file.close()
        self.irc_sever.close()
    def run(self):
        thread.start_new_thread(self.__recv_server, ())
        thread.start_new_thread(self.__recv_console, ())

        while True:
            if not self.message_queue.empty():
                message = self.message_queue.get()

                if message[0] == '/':
                    command = message.split(' ',1)[0]
                    if command == '/quit':
                        self.__send('QUIT :gone')
                        self.quit()
                        break
                elif message.split(' ')[0] == 'PING':
                    msg = 'PONG %s' % message.split(' ')[1]
                    print message
                    self.__log_message('server', message)
                    self.__send(msg)
                elif message.split(' ')[0] == 'QUIT':
                    self.quit()
                    break
                else:
                    message = self.__parse_message(message)
                    if message:
                        command = message[1][0]
                        if command == '001' or command == 'RPL_WELCOME':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_WELCOME '+msg)
                            print msg
                        elif command == '002' or command == 'RPL_YOURHOST':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('sever', 'RPL_YOURHOST '+msg)
                            print msg
                        elif command == '003' or command == 'RPL_CREATED':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_CREATED '+msg)
                            print msg
                        elif command == '004' or command == 'RPL_MYINFO':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_MYINFO '+msg)
                            print msg
                        elif command == '005' or command == 'RPL_ISUPPORT ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_ISUPPORT  '+msg)
                            print msg
                        elif command == '042' or command == 'RPL_YOURID ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_YOURID  '+msg)
                            print msg
                        elif command == '251' or command == 'RPL_LUSERCLIENT ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_LUSERCLIENT  '+msg)
                            print msg
                        elif command == '252' or command == 'RPL_LUSEROP ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_LUSEROP  '+msg)
                            print msg
                        elif command == '254' or command == 'RPL_LUSERCHANNELS ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_LUSERCHANNELS  '+msg)
                            print msg
                        elif command == '255' or command == 'RPL_LUSERME ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_LUSERME  '+msg)
                            print msg
                        elif command == '265' or command == 'RPL_LOCALUSERS ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_LOCALUSERS  '+msg)
                            print msg
                        elif command == '266' or command == 'RPL_GLOBALUSERS ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_GLOBALUSERS  '+msg)
                            print msg
                        elif command == '375' or command == 'RPL_MOTDSTART ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_MOTDSTART  '+msg)
                            self.motd = msg+'\n'
                            print msg
                        elif command == '372' or command == 'RPL_MOTD ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_MOTD  '+msg)
                            self.motd += msg+'\n'
                            print msg
                        elif command == '376' or command == 'RPL_ENDOFMOTD ':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'RPL_ENDOFMOTD  '+msg)
                            self.motd += msg
                            print msg
                        elif command == 'MODE':
                            msg = ' '.join(message[1][2:])
                            self.mode = msg
                            self.__log_message('server', 'MODE  '+msg)
                            print msg
                        elif command == 'NOTICE':
                            msg = ' '.join(message[1][2:])
                            self.__log_message('server', 'NOTICE  '+msg)
                            print msg
                        else:
                            print '%s : %s' %(message[0], message[1])

            time.sleep(0.01)
    def quit(self):
        time.sleep(3)
        self.irc_sever.close()
        self.log_file.close()
    def __send(self, message):
        print message
        self.__log_message('client', message)
        message = '%s\r\n' % message
        self.irc_sever.send(message)
    def nick(self, nick):
        self.__send('NICK ' + nick)
    def user(self, username, host, server, realname):
        message = 'USER %s %s %s :%s' %(username, host, server, realname)
        self.__send(message)
    def join(self, channel):
        message = 'JOIN %s' % channel
        self.__send(message)
    def privmsg(self, receiver, message):
        message = 'PRIVMSG %s :%s' %(receiver, message)
        self.send(message)
    def part(self, channel):
        message = 'PART %s' %channel
        self.part(message)
    def notice(self, receiver, message):
        message = 'NOTICE %s :%s' %(receiver, message)
        self.__send(message)
    def __recv_server(self):
        while True:
            self.buffer += self.irc_sever.recv(4096)
            if self.buffer == '':
                print 'Connection down'
                break
            else:
                messages = self.buffer.split('\r\n')
                for message in messages[:-1]:
                    self.message_queue.put(message)
                self.buffer = messages[-1]
    def __recv_console(self):
        while True:
            message = raw_input()
            self.message_queue.put(message)
    def __log_message(self, type, message):
        # timestamp
        date = time.gmtime()

        # format command for logfile
        msg = '%s : %s : %s\n' %(time.strftime("%a %d %b %Y %X %z", date ),type, message)

        # write command to logfile
        self.log_file.write(msg)
    def __parse_message(self, message):
        if message:
            prefix = message.split(':')[1].split(' ')[0]
            parameters = message.split(':')[1].split(' ')[1:]
            if len(parameters) > 1 and len(parameters[-1]):
                parameters.pop()
            if message.count(':') > 1:
                parameters.append(''.join(message.split(':')[2:]))
            return prefix, parameters
    def part1(self):
        self.nick(client.nickname)
        self.user(client.username, client.host, client.server, client.realname)

        def send_quit():
            self.message_queue.put('/quit')

        timer = Timer(120, send_quit)
        timer.start()
        self.run()


client = IrcClient()
client.part1()



