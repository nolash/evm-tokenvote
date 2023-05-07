# standard imports
import unittest
import logging
import os
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.block import block_latest
from chainlib.eth.address import to_checksum_address
from hexathon import same as same_hex
from eth_erc20 import ERC20
from giftable_erc20_token import GiftableToken

# local imports
from evm_tokenvote.unittest import TestEvmVoteAccounts
from evm_tokenvote.unittest.base import hash_of_foo
from evm_tokenvote import Voter
from evm_tokenvote import ProposalState


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

class TestVoteProtect(TestEvmVoteAccounts):

    def setUp(self):
        super(TestVoteProtect, self).setUp()
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], self.token_address, protect_supply=True)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.voter_address = to_checksum_address(r['contract_address'])
        logg.debug('published protected voter on address {} with hash {}'.format(self.voter_address, tx_hash))
       

    def test_propose(self):
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.accounts[0], hash_of_foo, 100)
        self.rpc.do(o)

        c = GiftableToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], self.alice, 1)
        self.rpc.do(o)

        self.backend.mine_blocks(100)

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
        self.assertEqual(proposal.state & ProposalState.CANCELLED, ProposalState.CANCELLED)


if __name__ == '__main__':
    unittest.main()
