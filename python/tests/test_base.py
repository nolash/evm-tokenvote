# standard imports
import unittest
import logging
import os
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.block import block_latest
from chainlib.eth.block import block_by_number
from hexathon import same as same_hex

# local imports
from evm_tokenvote.unittest import TestEvmVote
from evm_tokenvote import Voter
from evm_tokenvote import ProposalState


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

hash_of_foo = '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae'

class TestVoteBase(TestEvmVote):

    def test_propose(self):
        description = hash_of_foo
        nonce_oracle = RPCNonceOracle(self.accounts[1], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.accounts[1], description, 100)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = block_latest()
        block_height = self.rpc.do(o)

        o = c.get_proposal(self.voter_address, 0, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        proposal = c.parse_proposal(r)
        logg.debug('proposal {}'.format(proposal))
        self.assertTrue(same_hex(proposal.description_digest, description))
        self.assertEqual(proposal.supply, self.supply)
        self.assertEqual(proposal.total, 0)
        self.assertEqual(proposal.block_deadline, block_height + 100)
        self.assertEqual(proposal.target_vote_ppm, 500000)
        self.assertTrue(same_hex(proposal.proposer, self.alice))
        self.assertEqual(proposal.state, ProposalState.INIT)


if __name__ == '__main__':
    unittest.main()
