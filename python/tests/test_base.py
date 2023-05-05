# standard imports
import unittest
import logging
import os
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt

# local imports
from evm_tokenvote.unittest import TestEvmVote
from evm_tokenvote import Voter


logging.basicConfig(level=logging.DEBUG)

class TestVoteBase(TestEvmVote):

    def test_propose(self):
        description = os.urandom(32).hex()
        nonce_oracle = RPCNonceOracle(self.accounts[1], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.accounts[1], description, 100)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)


if __name__ == '__main__':
    unittest.main()
