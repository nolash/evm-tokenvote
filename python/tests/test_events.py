# standard imports
import unittest
import logging
import os
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.contract import ABIContractLogDecoder
from chainlib.eth.contract import ABIContractType
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

class TestVoteEvents(TestEvmVote):

    def test_event_propose(self):
        description = hash_of_foo
        nonce_oracle = RPCNonceOracle(self.ivan, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.ivan, description, 100)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)

        rlog = r['logs'][0]

        o = block_latest()
        now_block_height = self.rpc.do(o)

        topic = ABIContractLogDecoder()
        topic.topic('ProposalAdded')
        topic.typ(ABIContractType.UINT256)
        topic.typ(ABIContractType.UINT256)
        topic.typ(ABIContractType.UINT256)
        topic.apply(rlog['topics'], rlog['data'])
        self.assertEqual(int(topic.contents[0], 16), now_block_height + 100)
        self.assertEqual(int(topic.contents[1], 16), 500000)
        self.assertEqual(int(topic.contents[2], 16), 0)


    def test_event_complete(self):
        half_supply = int(self.initial_supply / 2)
        description = hash_of_foo
        nonce_oracle = RPCNonceOracle(self.ivan, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.ivan, description, 100)
        self.rpc.do(o)
       
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
        
        (tx_hash, o) = c.finalize_vote(self.voter_address, self.alice)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        rlog = r['logs'][0]

        topic = ABIContractLogDecoder()
        topic.topic('ProposalCompleted')
        topic.typ(ABIContractType.UINT256)
        topic.typ(ABIContractType.BOOLEAN)
        topic.typ(ABIContractType.BOOLEAN)
        topic.typ(ABIContractType.UINT256)
        topic.apply(rlog['topics'], [rlog['data']])
        self.assertEqual(int(topic.contents[0], 16), 0)
        self.assertEqual(int(topic.contents[1], 16), 0)
        self.assertEqual(int(topic.contents[2], 16), 0)
        self.assertEqual(int(topic.contents[3], 16), half_supply)
   

    def test_event_insufficient(self):
        half_supply = int(self.initial_supply / 2)
        description = hash_of_foo
        nonce_oracle = RPCNonceOracle(self.ivan, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.ivan, description, 100)
        self.rpc.do(o)

        self.backend.mine_blocks(100)

        (tx_hash, o) = c.finalize_vote(self.voter_address, self.ivan)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        rlog = r['logs'][0]

        topic = ABIContractLogDecoder()
        topic.topic('ProposalCompleted')
        topic.typ(ABIContractType.UINT256)
        topic.typ(ABIContractType.BOOLEAN)
        topic.typ(ABIContractType.BOOLEAN)
        topic.typ(ABIContractType.UINT256)
        topic.apply(rlog['topics'], [rlog['data']])
        self.assertEqual(int(topic.contents[0], 16), 0)
        self.assertEqual(int(topic.contents[1], 16), 0)
        self.assertEqual(int(topic.contents[2], 16), 1)
        self.assertEqual(int(topic.contents[3], 16), 0)


    def test_event_cancelled(self):
        half_supply = int(self.initial_supply / 2)
        description = hash_of_foo
        nonce_oracle = RPCNonceOracle(self.ivan, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.ivan, description, 100)
        self.rpc.do(o)
       
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.transfer(self.address, self.accounts[0], self.alice, half_supply)
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.alice, conn=self.conn)
        c = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.approve(self.address, self.alice, self.voter_address, half_supply)
        self.rpc.do(o)

        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.vote_cancel(self.voter_address, self.alice, half_supply)
        self.rpc.do(o)
        
        (tx_hash, o) = c.finalize_vote(self.voter_address, self.alice)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        rlog = r['logs'][0]

        topic = ABIContractLogDecoder()
        topic.topic('ProposalCompleted')
        topic.typ(ABIContractType.UINT256)
        topic.typ(ABIContractType.BOOLEAN)
        topic.typ(ABIContractType.BOOLEAN)
        topic.typ(ABIContractType.UINT256)
        topic.apply(rlog['topics'], [rlog['data']])
        self.assertEqual(int(topic.contents[0], 16), 0)
        self.assertEqual(int(topic.contents[1], 16), 1)
        self.assertEqual(int(topic.contents[2], 16), 0)
        self.assertEqual(int(topic.contents[3], 16), half_supply)


if __name__ == '__main__':
    unittest.main()
