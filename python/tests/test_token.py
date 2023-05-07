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


class TestVoteToken(TestEvmVoteProposal):

    def test_withdraw(self):
        c = Voter(self.chain_spec)
        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)

        half_supply = self.initial_supply / 2
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, half_supply)
        self.rpc.do(o)

        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, half_supply)
        self.rpc.do(o)

        c = ERC20(self.chain_spec)
        o = c.balance_of(self.voter_address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, half_supply)

        o = c.balance_of(self.address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, 0)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.withdraw(self.voter_address, self.alice)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        o = c.balance_of(self.voter_address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, half_supply)

        o = c.balance_of(self.address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, 0)

        c = Voter(self.chain_spec)
        o = c.get_proposal(self.voter_address, 0, sender_address=self.alice)
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.total, half_supply)

        o = block_latest()
        now_block_height = self.rpc.do(o)
        need_blocks = self.proposal_block_height + 100 - now_block_height + 1
        self.backend.mine_blocks(need_blocks)

        # after deadline withdraw is locked
        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.withdraw(self.voter_address, self.alice)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.total, half_supply)

        c = ERC20(self.chain_spec)
        o = c.balance_of(self.voter_address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, half_supply)

        o = c.balance_of(self.address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, 0)

        # scan + finalize unlocks tokens
        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 0)
        self.rpc.do(o)

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.trent)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.total, half_supply)

        (tx_hash, o) = c.withdraw(self.voter_address, self.alice)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        c = ERC20(self.chain_spec)
        o = c.balance_of(self.address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, half_supply)

        o = c.balance_of(self.voter_address, self.alice, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        balance = int(r, 16)
        self.assertEqual(balance, 0)



if __name__ == '__main__':
    unittest.main()
