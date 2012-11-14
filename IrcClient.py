import socket
import time
import threading
import re
import sys
import Queue

class ConsoleHandler(threading.Thread):
    """ Class for picking up input from console.

    Class that picks up input from console and adds it to queue.

    The nature of the class is to run endlessely while calling
    class is alive so the responsibility to kill this class lies with calling class.
    """
    command_queue = Queue.Queue()

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
    user_name = 'nickcave'
    real_name = 'duddi heimi3r'
    password = None
    console_handler = ConsoleHandler()
    MOTD = ""

    def __init__(self):
        """ Initialize IrcClient.

        loads value of host from console or if that fails, default_host variable.
        opens file for logging, if that fails terminates program.
        opens tcp connection to server, if that failes terminates program.
        """

        self.__load_host_from_console()
        self.__open_log_file()
        self.__get_tcp_connection()

        # start monitoring console for commands
        self.console_handler.start()

    def register(self):
        """ registers user to irc server

        checks if user has password, if so we send password message to irc server.
        we then send nick message to irc server and then we send user message to
        irc server. if any of those steps fails due to incorrect value user is asked
        to enter those values into the console and we try again, or user can type quit
        and terminate program.

        """

        # optional to send password to register on irc server
        if self.password is not None:
            self.__send_pass(self.password)
        self.__send_nick(self.nick)
        self.__send_user(self.user_name, self.host, 'bull', self.real_name)

    def run(self):
        """ runs irc client

        tries to register client to server
        monitors console and connection to irc server for input
        """

        #register user to irc server
        self.register()

        while True:
            # get possible commands from console
            if not self.console_handler.command_queue.empty():
                command = self.console_handler.command_queue.get()
                words = command.split(' ',1)
                if words[0].lower() == 'quit':
                    self.__send_quit(words[1])
                elif words[0].lower() == 'nick':
                    self.irc_nick(words[1])
                elif words[0].lower() == 'join':
                    self.irc_join(words[1])

            # check for response from irc server for 3 sec
            else:
                response = ""
                try:
                    response = self.irc_server.recv(4096)
                except socket.error:
                    pass
                else:
                    self.__process_response(response)

    def quit(self):
        """ close all open threads

        terminates console handler
        closes file stream to log file
        closes connection to irc server
        terminates program
        """

        self.console_handler._Thread__stop()
        self.log_file.close()
        self.irc_server.close()
        exit()

    def __send_pass(self, password):
        """ function for register password to irc server

         verifies password is on valid format according to BNF
         <middle> ::= <any *non-empty sequence of octets not including SPACE
                      or NUL or CR or LF, the first of whick may not be :>

        parameter: password, password client and server use for added security

        return true if sending pass message was successful, otherwise sends false
        """

        # validates password according to BNF <middle>
        not_valid = re.match('^:|(.*[ \0\r\n]+.*)|\A$', password)
        if not_valid:
            print 'Password was not valid, Password was : ***********'
            return False

        # send pass command to irc server
        return self.__send_message('PASS', password)

    def irc_nick(self, nick):
        self.__send_nick(nick)

    def irc_join(self, channel):
            self.__send_join(channel)

    def __send_join(self, channel):
        return self.__send_message('JOIN', channel)

    def __send_nick(self, nick):
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
        if not valid:
            print 'Nick was not valid, nick was : {0}'.format(nick)
            return False

        # send command to irc server
        return self.__send_message('NICK', nick)

    def __send_user(self, user_name, host, server, real_name):
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

    def __send_pong(self, pongmsg):
        """ function for sending pong to irc server
        """
        self.__send_message('PONG', pongmsg)

    def __send_pong_from_message(self, message):
        """ takes parameters from message and inserts into pongmsg
        """
        line = self.__eat_prefix(message)
        words = line.split(':')
        pongmsg = words[1]
        self.__send_pong(pongmsg)

    def __send_quit(self, quitmsg):
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
        quitmsg = ':%s' % quitmsg
        return self.__send_message('QUIT', quitmsg)

    def __send_message(self, command, parameter_list):
        """ function for sending message to irc serve

        validates message is not longer than 512 characters

        parameter: command, command of message.
        parameter: parameter_list, parameter list of message

        return true if we could send message
        return false if we could not send message
        """

        msg = '%s %s\r\n' %(command, parameter_list)
        # validate message is not longer than 512 char
        if len(msg) > 512:
            print 'message exceeded 512 chars, it was : {0} chars'.format(len(msg))
            return False

        # try send message to irc server
        try:
            self.irc_server.send(msg)
        except socket.error as e:
            print e.args

        # print message to console
        print msg.strip('\n')

        # log message to log file
        self.__log_message('client', msg.strip('\n'))

        # everything went ok
        return True

    def __load_host_from_console(self):
        """ assigns url of host.

        checks if url of host is first argument
        if not, host is set to default_host.
        irc.freenode.net

        """
        if len(sys.argv) > 1:
            self.host = sys.argv[1]

        # no arguments from console
        else:
            print 'Missing irc server url as argument in command line'
            print 'Signing up to default irc server %s' % self.default_host
            self.host = self.default_host

    def __open_log_file(self):
        """ opens file for logging.

        opens file for logging, if we fail to open file
        program terminates .
        """
        try:
            self.log_file = open('irc.log', 'a')
        except IOError as e:
            print 'Unable to open file at irc.log'
            print e.args
            exit(-1)

    def __get_tcp_connection(self):
        """ opens tcp connection to irc server.

        tries to establish tcp connection to irc serve with url
        in class variable host and port number in class variable port

        program terminates if we are unable to get connection
        """
        try:
            # open socket for connection
            self.irc_server = socket.socket()

            # set timout in case no response is comming.
            self.irc_server.settimeout(3)

            # trie to connect to irc server
            self.irc_server.connect((self.host, self.port))
        except socket.error as e:
            print 'Unable to connect to %s on port %i' %(self.host, self.port)
            print e.args
            exit(-1)

    def __log_message(self,source, msg):
        # timestamp
        date = time.gmtime()

        # format command for logfile
        msg = '%s : %s : %s' %(time.strftime("%a %d %b %Y %X %z", date ), source, msg)

        # write command to logfile
        self.log_file.write(msg)

    def __is_ping_message(self, response):
        line = self.__eat_prefix(response)
        match = re.match('^PING .*', line)
        if match:
            return  True
        return False

    def __is_start_of_MOTD(self, response):
        line = self.__eat_prefix(response)
        match = re.match('(^RPL_MOTDSTART .*)|(^375 .*)', line)
        if match:
            return True
        return False

    def __add_message_to_MOTD(self, message):
        words = message.split(' ',4)
        self.MOTD += words[4]
        self.__log_message('server', message.strip('\n'))

    def __is_MOTD(self, response):
        line = self.__eat_prefix(response)
        match = re.match('(^RPL_MOTD .*)|(^372 .*)', line)
        if match:
            return True
        return False

    def __is_end_MOTD(self, response):
        line = self.__eat_prefix(response)
        match = re.match('(^RPL_ENDOFMOTD .*)|(^376 .*)', line)
        if match:
            return True
        return False

    def __eat_prefix(self, message='1 1'):
        match = re.match('^:.*', message)
        if match:
            words = message.split(' ', 1)
            return words[1]
        else:
            return message

    def __process_response(self, buffer):
        # connection is down
        if buffer == '':
            print 'Connection went down'
            self.quit()
        else:
            # split into messages
            messages = buffer.splitlines(True)

            # check kind of each message
            for message in messages:

                # ping message
                if self.__is_ping_message(message):
                    self.__send_pong_from_message(message)

                # start of MOTD
                elif self.__is_start_of_MOTD(message):
                    self.__add_message_to_MOTD(message)

                # MOTD
                elif self.__is_MOTD(message):
                    self.__add_message_to_MOTD(message)

                # end of MOTD
                elif self.__is_end_MOTD(message):
                    self.__add_message_to_MOTD(message)
                    print self.MOTD

                else:
                    print message


client = IrcClient()
time.sleep(3)
client.run()
