# standard imports
import logging
import time

# external imports
from chainlib.eth.unittest.ethtester import EthTesterCase
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt
from chainlib.eth.address import to_checksum_address
from giftable_erc20_token.unittest import TestGiftableToken
#from giftable_erc20_token import GiftableToken
from eth_erc20 import ERC20
from chainlib.eth.block import block_latest
from eth_accounts_index.unittest import TestAccountsIndex
from eth_accounts_index.registry import AccountRegistry

# local imports
from evm_tokenvote import Voter

logg = logging.getLogger(__name__)

hash_of_foo = '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae'
hash_of_bar = 'fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9'
hash_of_baz = 'baa5a0964d3320fbc0c6a922140453c8513ea24ab8fd0577034804a967248096'


class TestEvmVoteAccounts(TestGiftableToken):

    expire = 0

    def setUp(self):
        super(TestEvmVoteAccounts, self).setUp()

        self.alice = self.accounts[1]
        self.bob = self.accounts[2]
        self.carol = self.accounts[3]
        self.dave = self.accounts[4]
        self.trent = self.accounts[5]
        self.mallory = self.accounts[8]
        self.ivan = self.accounts[9]

        self.conn = RPCConnection.connect(self.chain_spec, 'default')

        c = ERC20(self.chain_spec)
        o = c.total_supply(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.supply = int(r, 16)
        self.assertGreater(self.supply, 0)

        self.token_address = self.address


class TestEvmVote(TestEvmVoteAccounts):

    def setUp(self):
        super(TestEvmVote, self).setUp()

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], self.address)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.voter_address = to_checksum_address(r['contract_address'])
        logg.debug('published voter on address {} with hash {}'.format(self.voter_address, tx_hash))


class TestEvmVoteProposal(TestEvmVote):

    def setUp(self):
        super(TestEvmVoteProposal, self).setUp()
        description = hash_of_foo
        nonce_oracle = RPCNonceOracle(self.ivan, conn=self.conn)
        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.propose(self.voter_address, self.ivan, description, 100)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        o = block_latest()
        self.proposal_block_height = self.rpc.do(o)



class TestEvmVoteRegistry(TestEvmVoteAccounts):

    def setUp(self):
        super(TestEvmVoteRegistry, self).setUp()

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.conn)
        c = AccountRegistry(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0])
        self.conn.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.registry_address = r['contract_address']
        logg.debug('published with accounts registry (voter) contract address {}'.format(r['contract_address']))

        (tx_hash, o) = c.add_writer(self.registry_address, self.accounts[0], self.accounts[0])
        self.conn.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        (tx_hash, o) = c.constructor(self.accounts[0])
        self.conn.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.proposer_registry_address = r['contract_address']
        logg.debug('published with accounts registry (proposer) contract address {}'.format(r['contract_address']))

        (tx_hash, o) = c.add_writer(self.proposer_registry_address, self.accounts[0], self.accounts[0])
        self.conn.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)

        c = Voter(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], self.token_address, voter_registry_address=self.registry_address, proposer_registry_address=self.proposer_registry_address)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        self.assertEqual(r['status'], 1)
        self.voter_address = to_checksum_address(r['contract_address'])
        logg.debug('published voter on address {} with hash {}'.format(self.voter_address, tx_hash))
