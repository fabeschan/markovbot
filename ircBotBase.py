#!/usr/bin/env python

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log
import time, sys
from daemon import Daemon

class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, file):
        self.file = file

    def log(self, message):
        """Write a message to the file."""
        timestamp = "[%s]" % time.asctime(time.localtime(time.time()))
        self.file.write('%s %s\n' % (timestamp, message))
        self.file.flush()

    def close(self):
        self.file.close()

class IrcBotBase(irc.IRCClient):
    """IRC bot. Base form"""

    def __init__(self, nickname="ircbot"):
        self.nickname = nickname

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("Connected")

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("Disconnected")
        self.logger.close()

    def msg_delay(self, delay, channel, msg):
        reactor.callLater(delay, self.msg, channel, msg)

    # override these functions to handle different events
    def handle_whisper(self, user, msg):
        msg = "It isn't nice to whisper!  Play nice with the group."
        self.msg(user, msg)

    def handle_message(self, user, channel, msg):
        if msg.startswith(self.nickname + ":"):
            msg = "%s: I am a log bot" % user
            self.msg(channel, msg)
            self.msg_delay(3.5, channel, "{}: How are you?".format(user))

    def handle_action(self, user, msg):
        pass

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("Joined channel [%s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            self.handle_whisper(user, msg)

        # Otherwise it is a message
        else:
            self.handle_message(user, channel, msg)

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))
        self.handle_action(user, msg)

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'

class IrcBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, nickname, channel, filename, ircBot=IrcBotBase):
        self.nickname = nickname
        self.channel = channel
        self.filename = filename
        self.ircBot = ircBot

    def buildProtocol(self, addr):
        p = self.ircBot(self.nickname)
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()

class IrcDaemon(Daemon):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        log.startLogging(sys.stdout) # initialize logging
        self.f = IrcBotFactory('ircbot', 'bottest', '/tmp/test.log') # create factory protocol and application

    def run(self):
        reactor.connectTCP("irc.snoonet.org", 6667, self.f) # connect factory to this host and port
        reactor.run() # run bot

    def main(self):
        if len(sys.argv) == 2:
            if 'start' == sys.argv[1]:
                daemon.start()
            elif 'stop' == sys.argv[1]:
                daemon.stop()
            elif 'restart' == sys.argv[1]:
                daemon.restart()
            else:
                print "Unknown command"
                sys.exit(2)
            sys.exit(0)
        else:
            print "usage: %s start|stop|restart" % sys.argv[0]
            sys.exit(2)


if __name__ == "__main__":
    daemon = IrcDaemon('/tmp/{}.pid'.format(sys.argv[0]))
    daemon.main() # run it

