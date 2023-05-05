# standard imports
import logging
import time

# external imports
from chainlib.eth.unittest.ethtester import EthTesterCase
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.address import to_checksum_address

# local imports
from eth_erc20 import ERC20
from giftable_erc20_token.unittest import TestGiftableToken
from evm_tokenvote import Voter

logg = logging.getLogger(__name__)


class TestEvmVote(TestGiftableToken):

    expire = 0

    def setUp(self):
        super(TestEvmVote, self).setUp()
        self.conn = RPCConnection.connect(self.chain_spec, 'default')

        c = ERC20(self.chain_spec)
        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        supply = int(r, 16)
        self.assertGreater(supply, 0)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], self.address)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.voter_address = to_checksum_address(r['contract_address'])
        logg.debug('published voter on address {} with hash {}'.format(self.voter_address, tx_hash))
