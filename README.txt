Introduction
1 Overview
  1.1 Tooling
  1.2 Interoperability
  1.3 Publishing the contract
2 Proposal
  2.1 Parameters
    2.1.1 Deadline
  2.2 Target vote
  2.3 Options
  2.4 Creating a proposal
3 Voting
  3.1 Proposal context
  3.2 Options
  3.3 Cancellation votes
  3.4 How to vote
4 Results
  4.1 Finalizing the proposal
    4.1.1 Enhanced results
  4.2 Recovering tokens
Appendix A Proposal states
Introduction
************

1 Overview
**********

This smart contract enables voting on proposals using ERC20 tokens.

1.1 Tooling
===========

Tests and tools are implemented using the chainlib-eth
(https://pypi.org/project/chainlib-eth) python package.

   To learn more about the individual CLI tools mentioned in this
document, please refer to their individual man pages.  The man pages
should be installed as part of the python packages.

1.2 Interoperability
====================

The ‘evm-tokenvote’ contract implements the ‘cic-contracts:TokenVote’
interface.

1.3 Publishing the contract
===========================

In python, the smart contract can be published using the ‘constructor’
method of the ‘evm_tokenvote.Voter’ class.

   Also, constructor bytecode can be generated on the command-line using
‘chainlib-gen’.  Thereafter, ‘eth-gen’ can be used to publish the
contract through an rpc endpoint:

     # Make sure evm_tokenvote is in your PYTHONPATH
     $ chainlib-gen evm_tokenvote create --token_address <token_address> > data.bin
     $ eth-gas -p <rpc_url> -y <json_keyfile> [ --passphrase-file <file_with_keyfile_passphrase> ] --data data.bin -i <evm:chain:chain_id:common_name> -s -w 0

   The ‘token_address’ argument *MUST* be an existing and valid ‘ERC20’
contract.

2 Proposal
**********

Proposals are created with a 32-byte description.

   How the description should be interpreted is up to the client
application.

   A proposal may be a binary (yes or no) vote, or define a number of
different options to choose from.

2.1 Parameters
==============

The arguments required to create a proposal depends on the type of
proposal to create.

2.1.1 Deadline
--------------

The deadline must be defined for all proposals.

   It is defined as a period of number of blocks during which votes may
be made.

   If a vote has been completed before the deadline is over, the result
will be available immediately.

   The contract does not check the sanity of the deadline value.  For
example, setting the deadline to ‘1’ block wait will be useless as
voting will expire immediately.

2.2 Target vote
===============

The target vote must be defined for all proposals.

   This defines the minimum participation in the vote.  It is defined as
parts-per-million of the total supply of tokens.

   For example.  a value of ‘500000’ will require 50% of all tokens in
the vote.  A value of ‘1000000’ will require the full supply.

2.3 Options
===========

A proposal may define one or more options for voters to choose between.

   Options are defined as 32-byte hexadecimal values.  As with the
description, it is up to the client application to decide how to
interpret the values.

2.4 Creating a proposal
=======================

To create a proposal without options:

# solidity:
function propose(bytes32 _description, uint256 _blockWait, uint24 _targetVotePpm) public returns (uint256);

# chainlib-python:
def propose(self, contract_address, sender_address, description, block_deadline, tx_format=TxFormat.JSONRPC, id_generator=None)

# eth-encode CLI:
$ eth-encode --mode tx --signature propose -e <voter_contract_address> -y <keyfile_json> a:<token_address> u:<blocks_until_deadline> u:<target_vote_ppm>

   To create a proposal with options:

solidity:
function proposeMulti(bytes32 _description, uint256 _blockWait, uint24 _targetVotePpm) public returns (uint256);

chainlib-python:
def propose(self, contract_address, sender_address, description, block_deadline, options=[<options_hex>, ...])

   (Unfortunately, ‘eth-encode’ does not currently support dynamic array
arguments.)

3 Voting
********

Votes are defined in magnitudes of ERC20 tokens.

   A vote will transfer ERC20 tokens to the custody of the smart
contract for the duration of the voting.

   The smart contract uses the ‘transferFrom’ method to transfer tokens.
It is the caller’s responsibility to make the necessary token allowance
(using ‘approve’).  Votes with insufficient allowance will fail.

3.1 Proposal context
====================

Votes are always cast on the oldest proposal the has not been completed.

3.2 Options
===========

If multiple options exist, the token holder may freely distribute votes
between the options.

3.3 Cancellation votes
======================

In both proposals with and without options, votes can be cast to cancel
the proposal.

   For proposals with no or one option, the _cancel_ amounts to a vote
against the proposal.

   For proposals with two or more options, the _cancel_ amounts to a
vote against proposal and its all options.

3.4 How to vote
===============

In each case, make sure the necessary _allowance_ has been successfully
executed.

   For proposals without options, a simplified method can be called:

# solidity:
function vote(uint256 _value) public returns (bool);


# chainlib-python:
def vote(self, contract_address, sender_address, value)


# eth-encode CLI:
$ eth-encode --mode tx --signature vote -e <voter_contract_address> -y <keyfile_json> u:<value>

   For proposal with options, the call is slightly more verbose:

# solidity:
function voteOption(uint256 _optionIndex, uint256 _value) public returns (bool);


# chainlib-python:
def vote(self, contract_address, sender_address, option=<option_index>, value)


# eth-encode CLI:
$ eth-encode --mode tx --signature voteOption -e <voter_contract_address> -y <keyfile_json> u:<option_index> u:<value>

   To cast votes for cancellation, the call will be:

# solidity:
function voteCancel(uint256 _value) public returns (bool);


# chainlib-python:
def vote_cancel(self, contract_address, sender_address, value)


# eth-encode CLI:
$ eth-encode --mode tx --signature voteCancel -e <voter_contract_address> -y <keyfile_json> u:<value>

4 Results
*********

A proposal vote is completed if either of the following are true:

   • The deadline has been reached
   • Proposal contains zero or one options, and target participation has
     been reached.
   • Cancellation votes have the majority.

4.1 Finalizing the proposal
===========================

Once a proposal vote has been completed, the proposal must be explicitly
finalized.

   Finalization analyzes the results of the vote, and marks the proposal
state accordingly.

   It also moves the proposal cursor to activate the next proposal in
the queue.

   Finally, it releases the ERC20 tokens used for the vote.

   Finalization is performed using the ‘finalize()’ contract method.  It
will fail if used before the proposal vote has been _completed_.

4.1.1 Enhanced results
----------------------

The optional method ‘scan(uint256 _proposalIndex, uint256 _count’ can be
called on a completed proposal to further analyze the results of the
vote.

   In the current state of the contract, it will iterate the options of
the proposal, and mark the state as ‘TIED’ if two or more options have
the same amount of votes.

   This method may be called any time after proposal has been completed
(even before ‘finalize()’.  The proposal is identified by the
‘_proposalIndex’ parameter, where the index is the order of addition of
the proposal.

   The ‘_count’ parameter limits the amount of options that will be
scanned.  A consecutive call will start at the option where the previous
left off.

4.2 Recovering tokens
=====================

Before a new vote can take place, the ERC20 tokens used in previous
voting must be withdrawn.

   Withdrawal is performed using the ‘withdraw()’ contract method.  It
will fail if used before the proposal vote has been _finalized_.

Appendix A Proposal states
**************************

label bit   description
      value
------------------
INIT  1     Proposal
            has
            been
            initiated.
            It
            is
            used
            to
            disambiguate
            a
            proposal
            struct
            that
            has
            not
            yet
            been
            added,
            due
            to
            the
            ambiguity
            of
            the
            default
            struct
            value
            in
            solidity.
‘FINAL’2    ‘finalize()’
            has
            been
            successfully
            called.
‘SCANNED’4  ‘scan(...)’
            has
            been
            successfully
            called
            for
            all
            available
            options.
‘INSUFFICIENT’8Voting
            participation
            did
            not
            been
            the
            required
            target
            vote
            before
            the
            deadline.
‘TIED’16    Proposal
            contains
            two
            or
            more
            options,
            and
            two
            or
            more
            options
            have
            received
            the
            same
            amount
            of
            votes
            before
            the
            deadline.
‘SUPPLYCHANGE’32The
            token
            supply
            changed
            between
            when
            the
            proposal
            was
            added
            and
            voting
            ended.
            If
            supply
            is
            protected,
            this
            has
            also
            ‘CANCELLED’
            the
            vote.
‘IMMEDIATE’64Voting
            was
            completed
            before
            the
            deadline.
‘CANCELLED’128Interpretation
            depends
            on
            context.
            See
            below.

   Interpreting ‘CANCELLED’:

   • With ‘SUPPLYCHANGE’, this means that vote has been invalidated and
     should be discarded.
   • If proposal has options, it should be interpreted as that the
     existence of the proposal itself has been _rejected_.
   • With no or one option, it should be interpreted as the proposal has
     been _defeated_.
