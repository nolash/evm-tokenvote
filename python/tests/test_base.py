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

    def test_propose(self):
        c = Voter(self.chain_spec)
        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertTrue(same_hex(proposal.description_digest, hash_of_foo))
        self.assertEqual(proposal.supply, self.supply)
        self.assertEqual(proposal.total, 0)
        self.assertEqual(proposal.block_deadline, self.proposal_block_height + 100)
        self.assertEqual(proposal.target_vote_ppm, 500000)
        self.assertTrue(same_hex(proposal.proposer, self.ivan))
        self.assertEqual(proposal.state, ProposalState.INIT)

        o = c.current_proposal(self.voter_address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertTrue(same_hex(proposal.description_digest, hash_of_foo))
        self.assertEqual(proposal.supply, self.supply)
        self.assertEqual(proposal.total, 0)
        self.assertEqual(proposal.block_deadline, self.proposal_block_height + 100)
        self.assertEqual(proposal.target_vote_ppm, 500000)
        self.assertTrue(same_hex(proposal.proposer, self.ivan))
        self.assertEqual(proposal.state, ProposalState.INIT)



    def test_vote(self):
        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, 10)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, 100)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        o = c.get_proposal(self.voter_address, 0, sender_address=self.alice)
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.total, 0)

        # vote does not work without approval
        (tx_hash, o) = c.vote(self.voter_address, self.alice, 10)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, 100)
        self.rpc.do(o)

        # vote can be called multiple times (up to balance)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, 10)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.vote(self.voter_address, self.alice, 90)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        # vote total is updated
        o = c.get_proposal(self.voter_address, 0, sender_address=self.alice)
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.total, 100)

        # fail because all votes used
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, 1)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)


    def test_vote_win(self):
        half_supply = self.initial_supply / 2
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.bob, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, half_supply)
        self.rpc.do(o)

        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 0)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 0)

        o = block_latest()
        now_block_height = self.rpc.do(o)
        need_blocks = self.proposal_block_height + 100 - now_block_height + 1
        self.backend.mine_blocks(need_blocks)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.state, ProposalState.INIT)

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

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.trent)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.state & ProposalState.FINAL, ProposalState.FINAL)
        self.assertEqual(proposal.state & ProposalState.INSUFFICIENT, 0)
        self.assertEqual(proposal.state & ProposalState.TIED, 0)
        self.assertEqual(proposal.state & ProposalState.SUPPLYCHANGE, 0)


    def test_vote_insufficient(self):
        half_supply = self.initial_supply / 2
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.bob, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, half_supply)
        self.rpc.do(o)

        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote(self.voter_address, self.alice, half_supply - 1)
        self.rpc.do(o)

        o = block_latest()
        now_block_height = self.rpc.do(o)
        need_blocks = self.proposal_block_height + 100 - now_block_height + 1
        self.backend.mine_blocks(need_blocks)

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

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.trent)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.state & ProposalState.FINAL, ProposalState.FINAL)
        self.assertEqual(proposal.state & ProposalState.INSUFFICIENT, ProposalState.INSUFFICIENT)
        self.assertEqual(proposal.state & ProposalState.TIED, 0)
        self.assertEqual(proposal.state & ProposalState.SUPPLYCHANGE, 0)


    def test_proposal_invalid_supplychange(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = GiftableToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.alice, 1)
        self.rpc.do(o)

        o = block_latest()
        now_block_height = self.rpc.do(o)
        need_blocks = self.proposal_block_height + 100 - now_block_height + 1
        self.backend.mine_blocks(need_blocks)

        nonce_oracle = RPCNonceOracle(self.trent, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.scan(self.voter_address, self.trent, 0, 0)
        self.rpc.do(o)

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.trent)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        self.assertEqual(proposal.state & ProposalState.FINAL, ProposalState.FINAL)
        self.assertEqual(proposal.state & ProposalState.SUPPLYCHANGE, ProposalState.SUPPLYCHANGE)


if __name__ == '__main__':
    unittest.main()
