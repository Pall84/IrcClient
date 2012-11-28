
import sys
import socket
import time
import Queue
import thread
from threading import Timer
import platform
import readline


def dqn_to_int(st):
    """
    http://code.activestate.com/recipes/65219-ip-address-conversion-functions/#c3
    Convert dotted quad notation to integer
    "127.0.0.1" => 2130706433
    """
    st = st.split(".")
    ###
    # That is not so elegant as 'for' cycle and
    # not extensible at all, but that works faster
    ###
    return int("%02x%02x%02x%02x" % (int(st[0]),int(st[1]),int(st[2]),int(st[3])),16)


def int_to_dqn(st):
    """
    http://code.activestate.com/recipes/65219-ip-address-conversion-functions/#c3
    Convert integer to dotted quad notation
    """
    st = "%08x" % (st)
    ###
    # The same issue as for `dqn_to_int()`
    ###
    return "%i.%i.%i.%i" % (int(st[0:2],16),int(st[2:4],16),int(st[4:6],16),int(st[6:8],16))

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
        self.log_file =  open('irc.log', 'a')
        self.running = True
    def __del__(self):
        """ closes all streams in class deletion."""
        self.log_file.close()
        self.irc_sever.close()

    def start(self):
        """ Starts the irc client."""

        # open new threads for receiving input from console and irc server.
        thread.start_new_thread(self.__recv_server, ())
        thread.start_new_thread(self.__recv_console, ())

        # registers nick and user to irc server.
        self.__send('NICK '+client.nickname)
        self.__send_user(client.username, client.host, client.server, client.realname)

        # runs while client should be running.
        while self.running:

            # we have a message in queue
            if not self.message_queue.empty():

                # we retrieve message.
                message = self.message_queue.get()

                # handle empty string ( enter )
                if not message:
                    pass

                # this is ctcp command from console
                elif message.split(' ')[0] == '/ctcp':
                    self.__process_ctcp_console_command(message)

                # this is irc command from console
                elif message[0] == '/':
                    self.__process_irc_console_command(message)

                # this might be short command from server.
                elif len(message.split(' ')) < 3:
                    self.__process_irc_short_server_command(message)

                #this might be long command from server.
                else:
                    self.__process_irc_long_server_command(message)

            # rest
            time.sleep(0.05)
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

    def __send_user(self, username='', host='', server='', realname=''):
        """ send user message to irc server."""

        message = 'USER %s %s %s :%s' %(username, host, server, realname)
        self.__send(message)
    def __send(self, message):
        """ send messages to irc server."""

        # print, log and send message.
        self.printConsole( message )
        self.__log_message('client', message)
        self.irc_sever.send(message+'\r\n')

    def __process_irc_console_command(self, message):

        commands_without_trailer = 'NICK', 'JOIN', 'PART', 'NAMES', 'TRACE',\
                                   'MODE', 'LIST', 'INVITE', 'KICK',\
                                   'VERSION', 'STATS', 'LINKS', 'TIME', 'ADMIN',\
                                   'INFO', 'WHO', 'WHOIS', 'WHOWAS', 'ISON'

        commands_with_trailer = 'PRIVMSG', 'NOTICE', 'TOPIC'

        # retrieve irc command from message and make case insensitive.
        # remove '/' .
        command = message.split(' ',1)[0][1:].upper()

        if command in commands_without_trailer:

            parameter = ''

            # has parameter
            if len(message.split(' ')) > 1:
                parameter =  message.split(' ',1)[1]

            self.__send(command+' '+parameter)

        elif command in commands_with_trailer:

            parameter = ''
            trailer = ''

            # has parameter
            if len(message.split(' ')) > 1:
                parameter = message.split(' ')[1]

            # has trailer
            if len(message.split(' ')) > 2:
                trailer = ' :'+message.split(' ',2)[2]

            self.__send(command+' '+parameter+trailer)

        elif command == 'QUIT' or command == 'AWAY':

            trailer = ''

            # has trailer
            if len(message.split(' ')) > 1:
                trailer = ' :'+message.split(' ', 1)[1]

            self.__send(command+trailer)

        # we do not recognize the command and just print it to console.
        else:
            self.printConsole( message )
    def __process_irc_short_server_command(self, message):
        # retrieve command from message.
        command = message.split(' ', 1)[0]

        # check what kind of command and respond.
        if command == 'PING':
            # split message into command and server message.
            words = message.split(' ',1)

            # print, log and send pong response.
            self.printConsole( message )
            self.__log_message('server', message)
            self.__send('PONG '+words[1])

        elif command == 'QUIT':
            # print, log and terminate program.
            self.printConsole( message )
            self.__log_message('server', message)
            self.quit()

        # we have command which we do not recognize and only print it out to console
        else:
            self.printConsole( message )
    def __process_irc_long_server_command(self, message):

        irc_command = ['001', 'RPL_WELCOME'], ['002', 'RPL_YOURHOST'], ['003', 'RPL_CREATED'],\
                      ['004', 'RPL_MYINFO'], ['005', 'RPL_ISUPPORT'], ['042', 'RPL_YOURID'],\
                      ['200', 'RPL_TRACELINK'], ['201', 'RPL_TRACECONNECTING'], ['202', 'RPL_TRACEHANDSHAKE'],\
                      ['203', 'RPL_TRACEUNKNOWN'], ['204', 'RPL_TRACEOPERATOR'], ['205', 'RPL_TRACEUSER'],\
                      ['206', 'RPL_TRACESERVER'], ['208', 'RPL_TRACENEWTYPE'], ['211', 'RPL_STATSLINKINFO'],\
                      ['212', 'RPL_STATSCOMMANDS'], ['213', 'RPL_STATSCLINE'], ['214', 'RPL_STATSNLINE'],\
                      ['215', 'RPL_STATSILINE'], ['216', 'RPL_STATSKLINE'], ['217', 'RPL_STATSQLINE'],\
                      ['218', 'RPL_STATSYLINE'], ['219', 'RPL_ENDOFSTATS'], ['221', 'RPL_UMODEIS'],\
                      ['231', 'RPL_SERVICEINFO'], ['232', 'RPL_ENDOFSERVICES'], ['233', 'RPL_SERVICE'],\
                      ['241', 'RPL_STATSLLINE'], ['242', 'RPL_STATSUPTIME'], ['243', 'RPL_STATSOLINE'],\
                      ['244', 'RPL_STATSHLINE'], ['244', 'RPL_STATSHLINE'], ['251', 'RPL_LUSERCLIENT'],\
                      ['252', 'RPL_LUSEROP'], ['253', 'RPL_LUSERUNKNOWN'], ['254', 'RPL_LUSERCHANNELS'],\
                      ['255', 'RPL_LUSERME'], ['256', 'RPL_ADMINME'], ['257', 'RPL_ADMINLOC1'],\
                      ['258', 'RPL_ADMINLOC2'], ['259', 'RPL_ADMINEMAIL'], ['261', 'RPL_TRACELOG'],\
                      ['262', 'RPL_TRACEEND'], ['265', 'RPL_LOCALUSERS'], ['266', 'RPL_GLOBALUSERS'],\
                      ['300', 'RPL_NONE'], ['301', 'RPL_AWAY'], ['302', 'RPL_USERHOST'], ['303', 'RPL_ISON'],\
                      ['305', 'RPL_UNAWAY'], ['306', 'RPL_NOWAWAY'], ['311', 'RPL_WHOISUSER'],\
                      ['312', 'RPL_WHOISSERVER'], ['313', 'RPL_WHOISOPERATOR'], ['314', 'RPL_WHOWASUSER'],\
                      ['315', 'RPL_ENDOFWHO'], ['316', 'RPL_WHOISCHANOP'], ['317', 'RPL_WHOISIDLE'],\
                      ['318', 'RPL_ENDOFWHOIS'], ['319', 'RPL_WHOISCHANNELS'], ['321', 'RPL_LISTSTART'],\
                      ['322', 'RPL_LIST'], ['323', 'RPL_LISTEND'], ['324', 'RPL_CHANNELMODEIS'],\
                      ['331', 'RPL_NOTOPIC'], ['332', 'RPL_TOPIC'], ['341', 'RPL_INVITING'], \
                      ['342', 'RPL_SUMMONING'], ['351', 'RPL_VERSION'], ['352', 'RPL_WHOREPLY'],\
                      ['353', 'RPL_NAMREPLY'], ['361', 'RPL_KILLDONE'], ['362', 'RPL_CLOSING'],\
                      ['363', 'RPL_CLOSEEND'], ['364', 'RPL_LINKS'], ['365', 'RPL_ENDOFLINKS'],\
                      ['366', 'RPL_ENDOFNAMES'], ['367', 'RPL_BANLIST'], ['368', 'RPL_ENDOFBANLIST'],\
                      ['369', 'RPL_ENDOFWHOWAS'], ['371', 'RPL_INFO'], ['372', 'RPL_MOTD'],\
                      ['373', 'RPL_INFOSTART'], ['374', 'RPL_ENDOFINFO'], ['375', 'RPL_MOTDSTART'],\
                      ['376', 'RPL_ENDOFMOTD'], ['381', 'RPL_YOUREOPER'], ['382', 'RPL_REHASHING'],\
                      ['384', 'RPL_MYPORTIS'], ['391', 'RPL_TIME'], ['392', 'RPL_USERSSTART'],\
                      ['393', 'RPL_USERS'], ['394', 'RPL_ENDOFUSERS'], ['395', 'RPL_NOUSERS'],\
                      ['401', 'ERR_NOSUCHNICK'], ['402', 'ERR_NOSUCHSERVER'], ['403', 'ERR_NOSUCHCHANNEL'],\
                      ['404', 'ERR_CANNOTSENDTOCHAN'], ['405', 'ERR_TOOMANYCHANNELS'], ['406', 'ERR_WASNOSUCHNICK'],\
                      ['407', 'ERR_TOOMANYTARGETS'], ['409', 'ERR_NOORIGIN'], ['411', 'ERR_NORECIPIENT'],\
                      ['412', 'ERR_NOTEXTTOSEND'], ['413', 'ERR_NOTOPLEVEL'], ['414', 'ERR_WILDTOPLEVEL'],\
                      ['421', 'ERR_UNKNOWNCOMMAND'], ['422', 'ERR_NOMOTD'], ['423', 'ERR_NOADMININFO'],\
                      ['424', 'ERR_FILEERROR'], ['431', 'ERR_NONICKNAMEGIVEN'], ['432', 'ERR_ERRONEUSNICKNAME'],\
                      ['433', 'ERR_NICKNAMEINUSE'], ['436', 'ERR_NICKCOLLISION'], ['441', 'ERR_USERNOTINCHANNEL'],\
                      ['442', 'ERR_NOTONCHANNEL'], ['443', 'ERR_USERONCHANNEL'], ['444', 'ERR_NOLOGIN'],\
                      ['445', 'ERR_SUMMONDISABLED'], ['446', 'ERR_USERSDISABLED'], ['461', 'ERR_NEEDMOREPARAMS'],\
                      ['462', 'ERR_ALREADYREGISTERED'], ['463', 'ERR_NOPERMFORHOST'], ['464', 'ERR_PASSWDMISMATCH'],\
                      ['465', 'ERR_YOUREBANNEDCREEP'], ['466', 'ERR_YOUWILLBEBANNED'], ['466', 'ERR_KEYSET'],\
                      ['471', 'ERR_CHANNELISFULL'], ['472', 'ERR_UNKNOWNMODE'], ['473', 'ERR_INVITEONLYCHAN'],\
                      ['474', 'ERR_BANNEDFROMCHAN'], ['475', 'ERR_BADCHANNELKEY'], ['481', 'ERR_NOPRIVILEGES'],\
                      ['482', 'ERR_CHANOPRIVSNEEDED'], ['483', 'ERR_CANTKILLSERVER'], ['491', 'ERR_NOOPERHOST'],\
                      ['492', 'ERR_NOSERVICEHOST'], ['502', 'ERR_USERSDONTMATCH'], ['502', 'ERR_USERSDONTMATCH'],\
                      ['MODE', 'MODE'], ['TOPIC', 'TOPIC'],


        # parse message into command and parameter list.
        message = self.__parse_message(message)

       # retrieve command from message.
        command = message[1][0]

        # check what kind of command and respond.
        for c in irc_command:
            if command == c[0] or command == c[1]:
                # retrieve message, print and log it.
                message = ' '.join(message[1][2:])
                self.printConsole( message )
                self.__log_message('server', c[1]+' '+message)
                return

        # check what kind of command and respond.
        if command == 'NICK':
            self.nickname = message[1][1]

            # retrieve nick name, print and log it.
            message = '%s is now known as %s' %(message[0], message[1][1])
            self.printConsole( message )
            self.__log_message('server','NICK '+message)

        elif command == 'JOIN':
            # retrieve nick name, print and log it.
            message = '%s just joined %s' %(message[0], message[1][1])
            self.printConsole( message )
            self.__log_message('server','JOIN '+message)

        elif command == 'PART':
            # retrieve nick name, print and log it.
            message = '%s just left %s' %(message[0], message[1][1])
            self.printConsole( message )
            self.__log_message('server','PART '+message)

        elif command == 'NOTICE':
            # retrieve nick name, print and log it.
            nick_or_channel = ""
            if self.nickname == message[1][1]:
                nick_or_channel = message[0]
            else:
                nick_or_channel = "%s %s" %(message[1][1], message[0])
            message = '%s : %s' %(nick_or_channel, message[1][2])
            self.printConsole( message )
            self.__log_message('server','NOTICE '+message)

        elif command == 'PRIVMSG':
            #check if this is ctcp message
            if message[1][2][0] == '\001':
                self.__process_ctcp_server_command(message)
            else:
                # retrieve nick name, print and log it.
                nick_or_channel = ""
                if self.nickname == message[1][1]:
                    nick_or_channel = message[0]
                else:
                    nick_or_channel = "%s %s" %(message[1][1], message[0])
                message = '%s : %s' %(nick_or_channel, message[1][2])
                self.printConsole( message )
                self.__log_message('server','PRIVMSG '+message)

        # we have command which we do not recognize and only print it out to console
        else:
            self.printConsole( '%s : %s' %(message[0], message[1]) )

    def __process_ctcp_console_command(self, message):
        # retrieve command from message.
        words = message.split(' ')
        command = words[2].lower()
        if command == 'version':
            msg = "/privmsg %s %s" %(words[1],'\001VERSION\001' )
            self.message_queue.put(msg)
        else:
            self.printConsole( message )
    def __process_ctcp_server_command(self, message):
        command = message[1][2]
        event = message[1][2][1:len(message[1][2])-1].split(' ')

        if command == '\001VERSION\001':
            msg = "/privmsg %s %s" %(message[0], 'VERSION Python-Irc-Client' + " "
                    + platform.system() + " " + platform.release())
            self.message_queue.put(msg)
        elif event[0].upper() == "DCC" and event[1].upper() == "SEND":
            self.printConsole( event )
            thread.start_new_thread(self.__recv_DCC, (event[2], int(event[3]), int(event[4]), int(event[5]), message[0]) )
        else:
            self.printConsole( message )

    def __recv_DCC(self, filename, ip, port, datasize, nick=""):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((int_to_dqn(ip), port))
        except socket.error as e:
            msg = "/privmsg %s failed to connect to your host" %nick
            self.message_queue.put(msg)
        newFile = open(filename, 'wb')
        while True:
            da = s.recv(1024)
            if not da :
                break
            newFile.write(da)
            if newFile.tell() == datasize:
                break
        s.close()
        if newFile.tell() < datasize:
            msg = "/privmsg %s failed to recieve %s" %(nick, filename)
            self.message_queue.put(msg)
        else :
            message = "Success Transfer File from %s : %s" %(nick, filename)
            self.printConsole( message )
        newFile.close()

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
                self.running = False
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
            message = raw_input('> ')
            self.message_queue.put(message)
            time.sleep(0.5)
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

    # http://stackoverflow.com/a/4653306
    def printConsole(self,msg):
        sys.stdout.write('\r'+' '*(len(readline.get_line_buffer())+2)+'\r')
        print msg
        sys.stdout.write('> ' + readline.get_line_buffer())
        sys.stdout.flush()


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

client.start()

