# standard imports
import logging
import time

# external imports
from chainlib.eth.unittest.ethtester import EthTesterCase
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.address import to_checksum_address
from giftable_erc20_token.unittest import TestGiftableToken
#from giftable_erc20_token import GiftableToken
from eth_erc20 import ERC20
from chainlib.eth.block import block_latest

# local imports
from evm_tokenvote import Voter

logg = logging.getLogger(__name__)

hash_of_foo = '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae'


class TestEvmVote(TestGiftableToken):

    expire = 0

    def setUp(self):
        super(TestEvmVote, self).setUp()

        self.alice = self.accounts[1]
        self.bob = self.accounts[2]
        self.carol = self.accounts[3]
        self.dave = self.accounts[4]
        self.trent = self.accounts[5]
        self.mallory = self.accounts[8]
        self.ivan = self.accounts[9]

        self.conn = RPCConnection.connect(self.chain_spec, 'default')

        c = ERC20(self.chain_spec)
        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.supply = int(r, 16)
        self.assertGreater(self.supply, 0)
       
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], self.address)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.voter_address = to_checksum_address(r['contract_address'])
        logg.debug('published voter on address {} with hash {}'.format(self.voter_address, tx_hash))


class TestEvmVoteProposal(TestEvmVote):

    def setUp(self):
        super(TestEvmVoteProposal, self).setUp()
        description = hash_of_foo
        nonce_oracle = RPCNonceOracle(self.ivan, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.ivan, description, 100)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = block_latest()
        self.proposal_block_height = self.rpc.do(o)
