import socket
import time
import threading
import re
import sys
import Queue

class CommandsFromConsole(threading.Thread):
    """ Class for processing input from console."""
    command_queue = None

    # runs when function start is called
    def run(self):
        while True:
            self.command_queue.put(raw_input())


class IrcClient:
    """ Class for implementing irc client

    irc client use RFC 1459 standard

    """
    irc_server = None
    log_file = None
    response = None
    host = None
    default_host = 'irc.freenode.net'
    port = 6667
    nick = 'cave2'
    user_name = 'nickcave3'
    real_name = 'duddi heimi3r'
    password = None
    command_from_console = None
    command_queue = Queue.Queue()

    def __init__(self):
        """ Initialize IrcClient."""

        self.__load_host_from_console()
        self.__open_log_file()
        self.__get_tcp_connection()
        self.__setup_commands_from_console()

    def send_pong(self, pongmsg):
        """ function for sending pong to irc server
        """
        self.__send_message('PONG', pongmsg)

    def send_nick(self, nick):
        """ function for register nick to irc server

        verifies nick is on valid format according to BNF
        <nick> ::= <letter> { <letter> | <number> | <special> }
        <letter> ::= 'a'...'z' | 'A'...'Z'
        <number> ::= '0'...'9'
        <special> ::= '-' | '[' | ']' | '\' | '`' | '^' | '{' | '}'

        parameter: nick, nickname of user

        returns true if nick command was sent
        return false if nick command was not sent
        """

        # validates nick according to BNF <nick>
        valid = re.match('[a-zA-Z]([a-zA-Z]|[0-9]|[-\[\]\\`\^\{\}])*', nick)
        if not(valid):
            print 'Nick was not valid, nick was : {0}'.format(nick)
            return False

        # send command to irc server
        return self.__send_message('NICK', nick)

    def send_user(self, user_name, host, server, real_name):
        """ function for register user to irc server

        verifies username and realname is on valid format according to BNF
        <middle> ::= <any *non-empty sequence of octets not including SPACE
                      or NUL or CR or LF, the first of whick may not be :>

        <trailing> ::= <any, possible *empty*, sequence of octets not including
                        NUL or CR or LF

        parameter: username, username of user
        parameter: hostname, url of host
        parameter: servername, url of server
        parameter: realname, realname of user

        return true if user command was sent
        return false if user command was not sent
        """

        # validates username according to BNF <middle>
        not_valid = re.match('^:|(.*[ \0\r\n]+.*)|\A$', user_name)
        if not_valid:
            print 'Username was not valid, username was : %s' % user_name
            return False

        # validate realname according to BNF <trailing>
        not_valid = re.match('.*[\0\r\n]+.*', real_name)
        if not_valid:
            print 'Realname was not valid, realname was : %s' % real_name
            return False

        parameter_list = '%s %s %s :%s' %(user_name, host, server, real_name)

        # send user command to irc server
        return self.__send_message('USER', parameter_list)

    def send_quit(self, quitmsg):
        """ function for sending quit msg to irc server

        verifies quitmsg is on valid format according to BNF
        <trailing> ::= <any, possible *empty*, sequence of octets not including
                        NUL or CR or LF

        parameter: quitmsg, message that will be sent along quit command to irc server

        return true if quit command was sent
        return false if quit command was not sent
        """

        # validate quitmsg according to BNF <trailing>
        not_valid = re.match('.*[\0\r\n]+.*', quitmsg)
        if not_valid:
            print 'quit message was not valid, quit message was : %s' % quitmsg
            return False

        # send quit command to irc server
        return self.__send_message('QUIT', quitmsg)

    def __send_message(self, command, parameter_list):
        msg = unicode('%s %s\r\n' %(command, parameter_list))

        # validate command is not longer than 512 char
        if len(msg) > 512:
            print 'User command exceeded 512 chars, it was : {0} chars'.format(len(msg))
            return False
        try:
            self.irc_server.send(msg)
        except socket.error as e:
            print e.args
        # print command to console
        print msg.strip('\n')

        self.__log_message(msg.strip('\n'))

        # everything went ok
        return True

    def __open_log_file(self):
        try:
            self.log_file = open('irc.log', 'a')
        except IOError as e:
            print 'Unable to open file at irc.log'
            print e.args
            exit(-1)

    def __get_tcp_connection(self):
        try:
            self.irc_server = socket.socket()
            self.irc_server.connect((self.host, self.port))
        except socket.error as e:
            print 'Unable to connect to %s on port %i' %(self.host, self.port)
            print e.args
            exit(-1)

    def __load_host_from_console(self):
        if len(sys.argv) < 2:
            print 'Missing irc server url as argument in command line'
            print 'Signing up to default irc server %s' % self.default_host
            self.host = self.default_host
        else:
            self.host = sys.argv[1]

    def __setup_commands_from_console(self):
        self.command_from_console = CommandsFromConsole()
        self.command_from_console.command_queue = self.command_queue
        self.command_from_console.start()

    def __log_message(self, msg):
        # timestamp
        date = time.gmtime()

        # format command for logfile
        msg = '%s : client : %s' %(time.strftime("%a %d %b %Y %X %z", date ), msg)

        # write command to logfile
        self.log_file.write(msg)

    def register(self):

        if self.password is not None:
            "TODO send pass"
        self.send_nick(self.nick)
        self.send_user(self.user_name, self.host, 'bull', self.real_name)

    def run(self):
        while True:
            if not self.command_queue.empty():
                print self.command_queue.get()


client = IrcClient()
#time.sleep(3)
#client.register()
client.run()

# run while user does not type "quit"
command = ""
while command != 'quit':
    command = raw_input('Type quit to terminate irc client')

# send quit message to irc server
client.send_quit('done')