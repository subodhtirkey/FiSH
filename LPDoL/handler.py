from common import *
from twisted.internet import reactor

def repr_peer(peer_obj):
    return (peer_obj.uid, peer_obj.name)

class MessageHandler(object):
    def __init__(self, host_peer, ofstream):
        self.op_func=ofstream
        self.host=host_peer
        self.peer_list=set([])
        self.hook_gap=1
        #Mapping message keys to handling functions
        self.FUNC_CODES={
            1:self._respond_hook,
            2:self._del_peer,
            3:self._add_peer,
            4:self._name_taken}
        #Add HOOK trigger
        reactor.addSystemEventTrigger('after', 'startup', self.hook)
        if reactor.running:
            self.hook()
        #Add UNHOOK trigger
        reactor.addSystemEventTrigger('before', 'shutdown', self.unhook)

    def _respond_hook(self,source_peer,message):
        if source_peer.name in [x.name for x in peer_list]:
            if source_peer.name != 'anon':
                self.naming_conflict(source_peer)
                return             
        self.peer_list.add(source_peer)
        if not self.host.uid in message.data:
            self.live()

    def _name_taken(self,source_peer,message):
        if not self.host.name == 'anon':
            raise PeerDiscoveryError(1,'Name is already taken')
            self._paused=True
            
    def _add_peer(self,source_peer,message):
        self.peer_list.add(source_peer)
    
    def _del_peer(self,source_peer,message):
        self.peer_list.discard(source_peer)

    def handle(self,data,ip):
        try:
            message=LMessage(message_str=data)
        except MessageException as e:
            return -1
        source_uid, source_name=message.data[0]
        source_peer=Peer(uid=source_uid, name=source_name, addr=ip)
        self.FUNC_CODES[message.key](source_peer, message)
        
    def hook(self):
        '''Broadcasts a LPDOL_HOOK on Multicast group with exponential time delays'''
        #Generate list of peer UIDs
        peer_uid=map(repr_peer, self.peer_list)
        #Prefix host UID to list
        peer_uid.insert(0,repr_peer(self.host))
        message=LMessage(1,peer_uid)
        self.op_func(message)
        #Generate next time gap -- Exponential back-off
        if self.hook_gap < 256: self.hook_gap*=2
        #Register trigger with reactor
        reactor.callLater(self.hook_gap, self.hook)
    
    def naming_conflict(self,source_peer):
        '''Alerts a peer that the name is already in use'''
        message=LMessage(4,[repr_peer(source_peer)])
        self.op_func(message)

    def live(self):
        '''Asserts existance by broadcasting LPDOL_LIVE'''
        message=LMessage(3,[repr_peer(self.host)])
        self.op_func(message)

    def unhook(self):
        '''Broadcasts a LPDOL_UNHOOK message before disconnecting'''
        message=LMessage(2,[repr_peer(self.host)])
        self.op_func(message)
