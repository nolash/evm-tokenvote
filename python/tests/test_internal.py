# standard imports
import unittest
import logging
import os
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.block import block_latest
from hexathon import same as same_hex
from eth_erc20 import ERC20
from giftable_erc20_token import GiftableToken

# local imports
from evm_tokenvote.unittest import TestEvmVote
from evm_tokenvote.unittest.base import hash_of_foo
from evm_tokenvote import Voter
from evm_tokenvote import ProposalState


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

class TestVoteBase(TestEvmVote):

    def test_propose_internal_blockwait(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose_blockwait(self.voter_address, self.accounts[0], 123, 100)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.block_wait_limit(self.voter_address, sender_address=self.ivan)
        r = self.rpc.do(o)
        self.assertEqual(int(r, 16), 0)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.accounts[0], self.voter_address, self.initial_supply)
        self.rpc.do(o)

        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.accounts[0], self.initial_supply)
        self.rpc.do(o)

        (tx_hash, o) = c.scan(self.voter_address, self.accounts[0], 0, 0)
        self.rpc.do(o)

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.accounts[0])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.block_wait_limit(self.voter_address, sender_address=self.ivan)
        r = self.rpc.do(o)
        self.assertEqual(int(r, 16), 123) 

if __name__ == '__main__':
    unittest.main()
