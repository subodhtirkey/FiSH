from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver, FileSender
from twisted.internet import reactor
import json
from common import *
from indexer import *

SERVER_STATES={
    0:'HANDSHAKE',
    1:'FILE_TRANSFER'
    2:'BUSY'
}



class FileTransferDaemon(LineReceiver):
    def __init__(self, identity, file_indexer):
        self.STATE_FUNCTIONS={
            0:self.register_connection,
            1:self.transfer_file
            2:self.do_nothing}
        self.ident=identity
        self.indexer=file_indexer
        self.conn_peer=None
        self.rFn=None
        self.state = 0

    def addRefreshTrigger(self, refreshFn):
        self.rFn=refreshFn

    def connectionMade(self):
        self.sendLine(str(self.ident))

    def connectionLost(self, reason):
        pass

    def lineReceived(self, line):
        if not self.STATE_FUNCTIONS[self.state](line):
            self.transport.loseConnection()

    def register_connection(self, id):
        try:
            self.conn_peer=IdentString(data_str=id)
        except IdentException as e:
            self.sendLine('IDENTITY_ERR_{0}'.format(e))
            return False
        self.state=1
        self.sendLine(json.dumps(self.indexer.index))
        return True
        
    def transfer_file(self, fileHash):
        if not fileHash in self.indexer.index:
            self.sendLine('INVALID_FILE_ID')
            return False
        file_obj=self.indexer.getFile(fileHash)
        self.sendLine('SUCCESS_F_S')
        self.state=2
        fs=FileSender()
        self.transport.registerProducer(fs, streaming=False)
        d=fs.beginFileTransfer(file_obj, self.transport)
        d.addCallback(self.complete_transfer, True)
        d.addErrback(self.complete_transfer, False)
        return True

    def do_nothing(self, _):
        pass

    def complete_transfer(self, success):
        self.state=1
        if not success:
            
        pass

class IFFactory(Factory):
    def __init__(self, identity, indexer):
        self.id=identity
        self.inx=indexer

    def buildProtocol(self, addr):
        return FileTransferDaemon(self.id, self.inx)

if __name__ == '__main__':
    i=IdentString('vasuman','90d45d52450d11e2b59e94dbc9483303','127.0.0.1')
    reactor.listenTCP(8123, IFFactory(i, FileIndexer()))
    reactor.run()