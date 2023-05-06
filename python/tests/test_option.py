# standard imports
import unittest
import logging
import os
from chainlib.error import JSONRPCException
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.block import block_latest
from hexathon import same as same_hex
from eth_erc20 import ERC20
from giftable_erc20_token import GiftableToken

# local imports
from evm_tokenvote.unittest import TestEvmVote
from evm_tokenvote.unittest.base import hash_of_foo
from evm_tokenvote.unittest.base import hash_of_bar
from evm_tokenvote.unittest.base import hash_of_baz
from evm_tokenvote import Voter
from evm_tokenvote import ProposalState


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class TestVoteBase(TestEvmVote):

    def test_propose_multi(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.accounts[0], hash_of_foo, 100, options=[hash_of_bar, hash_of_baz])
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)

        o = c.get_option(self.voter_address, 0, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertTrue(same_hex(r, hash_of_bar))

        o = c.get_option(self.voter_address, 0, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.assertTrue(same_hex(r, hash_of_baz))

        with self.assertRaises(JSONRPCException):
            o = c.get_option(self.voter_address, 0, 2, sender_address=self.accounts[0])
            r = self.rpc.do(o)

        o = c.option_count(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        count = int(r, 16)
        self.assertEqual(count, 2)

        # check that vote count is accessible for the full options index
        o = c.vote_count(self.voter_address, 0, 1, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        count = int(r, 16)
        self.assertEqual(count, 0)

    
    def test_vote_multi(self):
        third_of_supply = int(self.initial_supply / 3)
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, third_of_supply)
        self.rpc.do(o)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.bob, third_of_supply)
        self.rpc.do(o)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.carol, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, third_of_supply)
        self.rpc.do(o)
        
        nonce_oracle = RPCNonceOracle(self.bob, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.bob, self.voter_address, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.carol, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.carol, self.voter_address, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.accounts[0], hash_of_foo, 100, options=[hash_of_bar, hash_of_baz])
        self.rpc.do(o)

        o = block_latest()
        proposal_block_height = self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, third_of_supply, option=1)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.bob, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.bob, third_of_supply, option=0)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.carol, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.carol, third_of_supply, option=1)
        self.rpc.do(o)

        o = block_latest()
        now_block_height = self.rpc.do(o)
        need_blocks = proposal_block_height + 100 - now_block_height + 1
        self.backend.mine_blocks(need_blocks)

        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 3) # count is 2, let's check 3 to see if the check catches it
        self.rpc.do(o)

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.trent)
        self.rpc.do(o)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)

        self.assertEqual(proposal.state & ProposalState.SCANNED, ProposalState.SCANNED)
        self.assertEqual(proposal.state & ProposalState.FINAL, ProposalState.FINAL)
        self.assertEqual(proposal.state & ProposalState.TIED, 0)
        self.assertEqual(proposal.state & ProposalState.INSUFFICIENT, 0)


    def test_vote_unanimous_fail(self):
        third_of_supply = int(self.initial_supply / 3)
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, third_of_supply)
        self.rpc.do(o)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.bob, third_of_supply)
        self.rpc.do(o)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.carol, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, third_of_supply)
        self.rpc.do(o)
        
        nonce_oracle = RPCNonceOracle(self.bob, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.bob, self.voter_address, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.carol, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.carol, self.voter_address, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.accounts[0], hash_of_foo, 100, target_vote_ppm=1000000, options=[hash_of_foo, hash_of_bar, hash_of_baz])
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, third_of_supply, option=1)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.bob, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.bob, third_of_supply, option=0)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.carol, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.carol, third_of_supply, option=1)
        self.rpc.do(o)

        o = block_latest()
        proposal_block_height = self.rpc.do(o)
        o = block_latest()
        now_block_height = self.rpc.do(o)

        need_blocks = proposal_block_height + 100 - now_block_height + 1
        self.backend.mine_blocks(need_blocks)

        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 3)
        self.rpc.do(o)

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.trent)
        self.rpc.do(o)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.state & ProposalState.SCANNED, ProposalState.SCANNED)
        self.assertEqual(proposal.state & ProposalState.FINAL, ProposalState.FINAL)
        self.assertEqual(proposal.state & ProposalState.TIED, 0)
        self.assertEqual(proposal.state & ProposalState.INSUFFICIENT, ProposalState.INSUFFICIENT)


    def test_vote_tied(self):
        third_of_supply = int(self.initial_supply / 3)
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, third_of_supply)
        self.rpc.do(o)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.bob, third_of_supply)
        self.rpc.do(o)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.carol, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, third_of_supply)
        self.rpc.do(o)
        
        nonce_oracle = RPCNonceOracle(self.bob, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.bob, self.voter_address, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.carol, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.carol, self.voter_address, third_of_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.accounts[0], hash_of_foo, 100, options=[hash_of_foo, hash_of_bar, hash_of_baz])
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, third_of_supply, option=1)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.bob, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.bob, third_of_supply, option=0)
        self.rpc.do(o)

        o = block_latest()
        proposal_block_height = self.rpc.do(o)
        o = block_latest()
        now_block_height = self.rpc.do(o)

        need_blocks = proposal_block_height + 100 - now_block_height + 1
        self.backend.mine_blocks(need_blocks)

        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 3)
        self.rpc.do(o)

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.trent)
        self.rpc.do(o)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.state & ProposalState.SCANNED, ProposalState.SCANNED)
        self.assertEqual(proposal.state & ProposalState.FINAL, ProposalState.FINAL)
        self.assertEqual(proposal.state & ProposalState.TIED, ProposalState.TIED)
        self.assertEqual(proposal.state & ProposalState.INSUFFICIENT, 0)


if __name__ == '__main__':
    unittest.main()
