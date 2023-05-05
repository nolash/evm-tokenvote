# standard imports
import logging
import os
import enum

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


class ProposalState(enum.IntEnum):
    INIT = 1
    FINAL = 2
    SCANNED = 4
    INSUFFICIENT = 8
    TIED = 16
    SUPPLYCHANGE = 32


class Proposal:
   
    def __init__(self, description_digest, *args, **kwargs):
        self.description_digest = description_digest
        self.supply = kwargs.get('supply')
        self.total = kwargs.get('total')
        self.block_deadline = kwargs.get('block_deadline')
        self.target_vote_ppm = kwargs.get('target_vote_ppm')
        self.proposer = kwargs.get('proposer')
        self.state = kwargs.get('state')
        self.serial = kwargs.get('serial')


    def __str__(self):
        return "proposal with description: " + self.description_digest


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


    def get_proposal(self, contract_address, proposal_idx, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('proposals')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(proposal_idx)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    @classmethod
    def parse_proposal(self, v, serial=None):
        v = strip_0x(v)
        logg.debug("proposal {}".format(v))

        cursor = 0
        dec = ABIContractDecoder()
        dec.typ(ABIContractType.BYTES32)
        dec.typ(ABIContractType.UINT256)
        dec.typ(ABIContractType.UINT256)
        dec.typ(ABIContractType.UINT256)
        dec.typ(ABIContractType.UINT256) # actually uint24
        dec.typ(ABIContractType.ADDRESS)
        dec.typ(ABIContractType.UINT8)
        dec.val(v[cursor:cursor+64])
        #cursor += 64 # options pos
        #cursor += 64 # optionsvotes pos
        cursor += 64
        dec.val(v[cursor:cursor+64])
        cursor += 64
        dec.val(v[cursor:cursor+64])
        cursor += 64
        dec.val(v[cursor:cursor+64])
        cursor += 64
        dec.val(v[cursor:cursor+64])
        cursor += 64
        dec.val(v[cursor:cursor+64])
        cursor += 64
        dec.val(v[cursor:cursor+64])

        r = dec.get()
        logg.debug('rrr {}'.format(r))
        o = Proposal(r[0],
                     supply=r[1],
                     total=r[2],
                     block_deadline=r[3],
                     target_vote_ppm=r[4],
                     proposer=r[5],
                     state=r[6],
                     serial=serial,
                     )
        return o
