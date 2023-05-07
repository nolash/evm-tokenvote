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
from evm_tokenvote.unittest import TestEvmVoteProposal
from evm_tokenvote.unittest.base import hash_of_foo
from evm_tokenvote import Voter
from evm_tokenvote import ProposalState


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

class TestVoteBase(TestEvmVoteProposal):

    def test_cancel(self):
        half_supply = int(self.initial_supply / 2)
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, half_supply)
        self.rpc.do(o)

        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote_cancel(self.voter_address, self.alice, half_supply - 1)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 0)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote_cancel(self.voter_address, self.alice, 1)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 0)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.state & ProposalState.SCANNED, ProposalState.SCANNED)
        self.assertEqual(proposal.state & ProposalState.IMMEDIATE, ProposalState.IMMEDIATE)
        self.assertEqual(proposal.state & ProposalState.CANCELLED, ProposalState.CANCELLED)


if __name__ == '__main__':
    unittest.main()
