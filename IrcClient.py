__author__ = 'Palli'

import sys
import socket
import time
import Queue
import thread
from threading import Timer
import re

class IrcClient(object):
    """ Internet Relay Char Client.

    Simple irc client with minimalistic functionality.
    Implements some of RFC 1459, http://tools.ietf.org/html/rfc1459.html.
    Coding style according to Google Python Code Style,
    http://google-styleguide.googlecode.com/svn/trunk/pyguide.html.

    client is initialized with default values.
       nickname = defaultNick.
       username = defaultUsername.
       server = defaultServer.
       realname = default real name.
       log_file = opens file at relative url from root of program irc.log.
       running = True.

    To start client we need to call function run.
    To end client we need to call function quit.

    client closes log_file and irc_server on deletion

    Attributes:
        host: url of irc server.
        irc_server: tcp connection to irc server.
        nickname: nick name of user.
        username: username of user.
        server: url or irc client.
        realname: real name of user.
        buffer: buffer for keeping response from irc server.
        message_queue: queue for all messages, either from console or irc server.
        log_file: file for logging messages, retrieved or sent.
            in the format Date : source (server/client) : message.
        running: boolean value for if client should be running.
    """

    def __init__(self):
        """ Initialize class with default values."""
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
        self.running = True
    def __del__(self):
        """ closes all streams in class deletion."""
        self.log_file.close()
        self.irc_sever.close()
    def run(self):
        """ Runs the irc client."""

        # open new threads for receiving input from console and irc server.
        thread.start_new_thread(self.__recv_server, ())
        thread.start_new_thread(self.__recv_console, ())

        # runs while client should be running.
        while self.running:

            # we have a message in queue
            if not self.message_queue.empty():

                # we retrieve message.
                message = self.message_queue.get()

                # handle empty string ( enter )
                if not message:
                    pass

                elif message.split(' ')[0] == '/ctcp':
                    self.__process_ctcp_console_command(message)

                # this is command from console
                elif message[0] == '/':
                    self.__process_console_command(message)

                # this might be short command from server.
                elif len(message.split(' ')) < 3:
                    self.__process_short_server_command(message)

                #this might be long command from server.
                else:
                    self.__process_long_server_command(message)

            # sleep for 0.05 second to reduce load on processor.
            #time.sleep(0.05)
    def __process_console_command(self, message):
        # retrieve command from message and make case insensitive.
        command = message.split(' ',1)[0].lower()

        # check what kind of command and respond.
        if command == '/quit':
            # split message into command and quit message.
            words = message.split(' ',1)

            # quit message was included
            if len(words) > 1:
                self.__send('QUIT :'+words[1])

            # quit message was not included
            else:
                self.__send('QUIT')

            # terminate program
            self.quit()

        elif command == '/notice':
            # split message into command, receiver and notice message.
            words = message.split(' ',2)

            # validate message is not missing any part.
            if len(words) > 2:
                self.notice(words[1], words[2])
            # message was missing receiver or notice message and we do nothing.

        elif command == '/nick':
            # split message into command and nick name.
            words = message.split(' ',1)

            # validate nick name is not missing.
            if len(words) > 1:
                self.nick(words[1])

            # message is missing channel name and we let server handle error checking.
            else:
                self.nick()

        elif command == '/join':
            # split message into command and channel name.
            words = message.split(' ', 1)

            # validate channel name is not missing
            if len(words) > 1:
                self.join(words[1])
            # message is missing channel name and we let server handle error checking.
            else:
                self.join()

        elif command == '/part':
            # split message into command and channel name.
            words = message.split(' ', 1)

            # validate channel name is not missing
            if len(words) > 1:
                self.part(words[1])

            # message is missing channel name and we let server handle error checking.
            else:
                self.part()

        elif command == '/msg':
            # split message into command, receiver and private message.
            words = message.split(' ', 2)

            # validate receiver and private message is not missing.
            if len(words) > 2:
                self.privmsg(words[1], words[2])
            # message was missing receiver or private message and we do nothing.

        elif command == '/ctcp':
            # split message into command, receiver and action.
            words = message.split(' ', 2)

            # validate receiver and private message is not missing.
            if len(words) > 2:
                self.privmsg(words[1], words[2])
                # message was missing receiver or private message and we do nothing.

        elif command =='/names':
            # split message into command and channel name.
            words = message.split(' ', 1)

            # channel name is not missing
            if len(words) > 1:
                self.name(words[1])

            # no channel name
            else:
                self.name()

        elif command =='/trace':
            # split message into command and target.
            words = message.split(' ', 1)

            # channel name is not missing
            if len(words) > 1:
                self.trace(words[1])

            # no target
            else:
                self.trace()

        else:
            # we have command which we do not recognize and only print it out to console
            print message
    def __process_short_server_command(self, message):
        # retrieve command from message.
        command = message.split(' ', 1)[0]

        # check what kind of command and respond.
        if command == 'PING':
            # split message into command and server message.
            words = message.split(' ',1)

            # print, log and send pong response.
            print message
            self.__log_message('server', message)
            self.__send('PONG '+words[1])

        elif command == 'QUIT':
            # print, log and terminate program.
            print message
            self.__log_message('server', message)
            self.quit()

        # we have command which we do not recognize and only print it out to console
        else:
            print message
    def __process_long_server_command(self, message):
        # parse message into command and parameter list.
        message = self.__parse_message(message)

        # retrieve command from message.
        command = message[1][0]

        # check what kind of command and respond.
        if command == '001' or command == 'RPL_WELCOME':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_WELCOME '+message)

        elif command == '002' or command == 'RPL_YOURHOST':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_YOURHOST '+message)

        elif command == '003' or command == 'RPL_CREATED':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_CREATED '+message)

        elif command == '004' or command == 'RPL_MYINFO':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_MYINFO '+message)

        elif command == '005' or command == 'RPL_ISUPPORT ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_ISUPPORT  '+message)

        elif command == '042' or command == 'RPL_YOURID ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_YOURID  '+message)

        elif command == '200' or command == 'RPL_TRACELINK ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACELINK  '+message)

        elif command == '201' or command == 'RPL_TRACECONNECTING ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACECONNECTING  '+message)

        elif command == '202' or command == 'RPL_TRACEHANDSHAKE ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACEHANDSHAKE  '+message)

        elif command == '203' or command == 'RPL_TRACEUNKNOWN ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACEUNKNOWN  '+message)

        elif command == '204' or command == 'RPL_TRACEOPERATOR ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACEOPERATOR  '+message)

        elif command == '205' or command == 'RPL_TRACEUSER ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACEUSER  '+message)

        elif command == '206' or command == 'RPL_TRACESERVER ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACESERVER  '+message)

        elif command == '251' or command == 'RPL_LUSERCLIENT ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_LUSERCLIENT  '+message)

        elif command == '252' or command == 'RPL_LUSEROP ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_LUSEROP  '+message)

        elif command == '254' or command == 'RPL_LUSERCHANNELS ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_LUSERCHANNELS  '+message)

        elif command == '255' or command == 'RPL_LUSERME ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_LUSERME  '+message)

        elif command == '262' or command == 'RPL_TRACEEND ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_TRACEEND  '+message)

        elif command == '265' or command == 'RPL_LOCALUSERS ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_LOCALUSERS  '+message)

        elif command == '266' or command == 'RPL_GLOBALUSERS ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_GLOBALUSERS  '+message)

        elif command == '353' or command == 'RPL_NAMREPLY ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][3:])
            print message
            self.__log_message('server', 'RPL_NAMREPLY  '+message)

        elif command == '366' or command == 'RPL_ENDOFNAMES ':
            # retrieve message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_ENDOFNAMES  '+message)

        elif command == '375' or command == 'RPL_MOTDSTART ':
            # retrieve MOTD message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_MOTDSTART  '+message)

            # add start of MOTD to clients motd.
            self.motd = message+'\n'

        elif command == '372' or command == 'RPL_MOTD ':
            # retrieve MOTD message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_MOTD  '+message)

            # add MOTD to clients motd.
            self.motd += message+'\n'

        elif command == '376' or command == 'RPL_ENDOFMOTD ':
            # retrieve MOTD message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'RPL_ENDOFMOTD  '+message)

        elif command == '401' or command == 'ERR_NOSUCHNICK ':
            # retrieve error message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'ERR_NOSUCHNICK  '+message)

        elif command == '402' or command == 'ERR_NOSUCHSERVER ':
            # retrieve error message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'ERR_NOSUCHSERVER  '+message)

        elif command == '403' or command == 'ERR_NOSUCHCHANNEL ':
            # retrieve error message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'ERR_NOSUCHCHANNEL  '+message)

        elif command == '461' or command == 'ERR_NEEDMOREPARAMS ':
            # retrieve error message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'ERR_NEEDMOREPARAMS  '+message)

            # add end of MOTD to clients motd.
            self.motd += message

        elif command == 'MODE':
            # retrieve mode message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'MODE  '+message)

            # set clients mode to message.
            self.mode = message

        elif command == 'NOTICE':
            # retrieve notice message, print and log it.
            message = ' '.join(message[1][2:])
            print message
            self.__log_message('server', 'NOTICE  '+message)

        elif command == 'NICK':
            self.nickname = message[1][1]

            # retrieve nick name, print and log it.
            message = '%s is now known as %s' %(message[0], message[1][1])
            print message
            self.__log_message('server','NICK '+message)

        elif command == 'JOIN':
            # retrieve nick name, print and log it.
            message = '%s just joined %s' %(message[0], message[1][1])
            print message
            self.__log_message('server','JOIN '+message)

        elif command == 'PART':
            # retrieve nick name, print and log it.
            message = '%s just left %s' %(message[0], message[1][1])
            print message
            self.__log_message('server','PART '+message)

        elif command == 'PRIVMSG':
            #check if this is ctcp message
            if message[1][2][0] == '\001':
                self.__process_ctcp_server_command(message)
            else:
                # retrieve nick name, print and log it.
                message = '%s : %s' %(message[1][1], message[1][2])
                print message
                self.__log_message('server','PRIVMSG '+message)

        # we have command which we do not recognize and only print it out to console
        else:
            print '%s : %s' %(message[0], message[1])
    def __process_ctcp_server_command(self, message):
        command = message[1][2]

        if command == '\001VERSION\001':
            self.notice(message[0], 'VERSION Python-Irc-Client')
        else:
            print message
    def __process_ctcp_console_command(self, message):
        # retrieve command from message.
        command = message.split(' ')[2].lower()
        if command == 'version':
            self.privmsg(message.split(' ')[1], '\001VERSION\001')
        else:
            print message
    def quit(self):
        """ terminates irc client."""

        # tell client to stop running.
        self.running = False

        # wait few seconds to pick up last messages from server.
        time.sleep(3)

        # close server and log file connections.
        self.irc_sever.close()
        self.log_file.close()

        # terminate program
        exit(0)
    def __send(self, message):
        """ send messages to irc server."""

        # print, log and send message.
        print message
        self.__log_message('client', message)
        self.irc_sever.send(message+'\r\n')
    def nick(self, nick=''):
        """ send nick message to irc server."""

        self.__send('NICK ' + nick)
    def user(self, username='', host='', server='', realname=''):
        """ send user message to irc server."""
        message = 'USER %s %s %s :%s' %(username, host, server, realname)
        self.__send(message)
    def join(self, channel=''):
        """ send join message to irc server."""

        self.__send('JOIN '+channel)
    def privmsg(self, receiver='', message=''):
        """ send private message to irc server."""

        message = ':%s PRIVMSG %s :%s' %(self.nickname,receiver, message)
        self.__send(message)
    def part(self, channel=''):
        """ send part message to irc server."""

        self.__send('PART '+channel)
    def notice(self, receiver='', message=''):
        """ send notice message to irc server."""

        message = 'NOTICE %s :%s' %(receiver, message)
        self.__send(message)
    def name(self, message=''):
        """ send name message to irc server."""

        self.__send('NAMES '+message)
    def trace(self, target=''):
        """ trace a path across irc network to target."""

        self.__send('TRACE '+target)
    def __recv_server(self):
        """ retrieves message from irc server.

        Runs in constant loop while connection to irc server is up.
        In each iteration we retrieve response from irc server and add
        it to buffer which contains end of last response.
        We split buffer into list of message on '\r\n' and add all but last
        element to message queue of client, we finish by setting
        buffer to last element in list of messages.
        If end of response is complete message last element is '' otherwise
        last element is incomplete message.
        """

        # runs while connection to server is up.
        while True:

            # retrieve response from irc server and add to buffer.
            self.buffer += self.irc_sever.recv(4096)

            # if buffer is empty we know connection is down, and we stop the while loop.
            if self.buffer == '':
                print 'Connection down'
                break

            # we process response from server.
            else:

                # split response into messages on '\r\n'.
                messages = self.buffer.split('\r\n')

                # add each but the last message to message queue of client.
                for message in messages[:-1]:
                    self.message_queue.put(message)

                # set buffer to last message in response.
                # is '' if last message was complete.
                # is 1 or more chars otherwise.
                self.buffer = messages[-1]
    def __recv_console(self):
        """ retrieves message from console.

        Runs in a constant loop while client is running..
        In each iteration we retrieve  response from console and add
        it to message queue of client.
        """

        # runs while client is running.
        while self.running:

            # retrieve message from console and add to message queue of client.
            message = raw_input()
            self.message_queue.put(message)
    def __log_message(self, type, message):
        """ log message to log file

        Logs sent and retrieved messages to log file in the format
            Date : source (server/client) : message.

        Args:
            message: message we want to log.
        """

        # timestamp
        date = time.gmtime()

        # format log message for log file in the format
        # Date : source (server/client) : message.
        msg = '%s : %s : %s\n' %(time.strftime("%a %d %b %Y %X %z", date ),
                                 type, message)

        # write log message to log file
        self.log_file.write(msg)
    def __parse_message(self, message):
        """ split message into prefix and list of parameters.

        We assume the message has the form :prefix list_of_parameters.

        Args:
            message: message we want to parse

        Returns:
            A tuple of prefix who is string and parameter list who is tuple of strings.
        """

        # validate message is not empty
        if message:

            # retrieve prefix from message.
            # first split gives us the list
            #        ['', prefix + parameters ], (possible) trailer ].
            # second split gives us prefix from the element prefix + parameters.
            prefix = message.split(':')[1].split(' ')[0]

            # retrieve list of parameters from message.
            parameters = message.split(':')[1].split(' ')[1:]

            # we have more than 1 ':' in message and then we know message contains trailer.
            if message.count(':') > 1:

                # add trailer to list of parameters.
                parameters.append(''.join(message.split(':')[2:]))

            try:
                parameters.remove('')
            except ValueError:
                pass

            return prefix, parameters
    def part1(self):
        """ runs part 1 assignment """

        # register to irc server.
        self.nick(client.nickname)
        self.user(client.username, client.host, client.server, client.realname)

        # terminates program
        def send_quit():
            self.message_queue.put('/quit')

        timer = Timer(120, send_quit)
        timer.start()
        self.run()



client = IrcClient()

# function for running part 1 of assignment

# note
# in function we are using time out function in separate thread.
# who sends quit command after 2 min. but because this thread
# is alive. main program does not terminate until after 2 min if user decides
# to terminate sooner than 2 min.

#client.part1()

client.nick(client.nickname)
client.user(client.username, client.host, client.server, client.realname)
client.run()

