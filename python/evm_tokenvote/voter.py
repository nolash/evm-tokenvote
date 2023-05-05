# standard imports
import logging
import os

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.contract import (
    ABIContractEncoder,
    ABIContractDecoder,
    ABIContractType,
    abi_decode_single,
)
from chainlib.eth.jsonrpc import to_blockheight_param
from chainlib.eth.error import RequestMismatchException
from chainlib.eth.tx import (
    TxFactory,
    TxFormat,
)
from chainlib.jsonrpc import JSONRPCRequest
from chainlib.block import BlockSpec
from hexathon import (
    add_0x,
    strip_0x,
)

# local imports
from evm_tokenvote.data import data_dir

logg = logging.getLogger()


class Voter(TxFactory):

    __abi = None
    __bytecode = None

    def constructor(self, sender_address, token_address, accounts_registry_address=None, tx_format=TxFormat.JSONRPC, version=None):
        code = self.cargs(token_address, accounts_registry_address=accounts_registry_address)
        tx = self.template(sender_address, None, use_nonce=True)
        tx = self.set_code(tx, code)
        return self.finalize(tx, tx_format)


    @staticmethod
    def cargs(token_address, accounts_registry_address=None, version=None):
        if accounts_registry_address == None:
            accounts_registry_address = ZERO_ADDRESS
        if token_address == None:
            raise ValueError("token address cannot be zero address")
        code = Voter.bytecode(version=version)
        enc = ABIContractEncoder()
        enc.address(token_address)
        enc.address(accounts_registry_address)
        args = enc.get()
        code += args
        logg.debug('constructor code: ' + args)
        return code


    @staticmethod
    def gas(code=None):
        return 4000000



    @staticmethod
    def abi():
        if Voter.__abi == None:
            f = open(os.path.join(data_dir, 'Voter.json'), 'r')
            Voter.__abi = json.load(f)
            f.close()
        return Voter.__abi


    @staticmethod
    def bytecode(version=None):
        if Voter.__bytecode == None:
            f = open(os.path.join(data_dir, 'Voter.bin'))
            Voter.__bytecode = f.read()
            f.close()
        return Voter.__bytecode



    def propose(self, contract_address, sender_address, description, block_deadline, target_vote_ppm=500000, tx_format=TxFormat.JSONRPC, id_generator=None):
        enc = ABIContractEncoder()
        enc.method('propose')
        enc.typ(ABIContractType.BYTES32)
        enc.typ(ABIContractType.UINT256)
        enc.typ_literal('uint24')
        enc.bytes32(description)
        enc.uint256(block_deadline)
        enc.uintn(target_vote_ppm, 24)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format, id_generator=id_generator)
        return tx

