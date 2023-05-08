::: {#Top .top-level-extent}
::: nav-panel
Next: [Overview](#overview){accesskey="n" rel="next"}  
\[[Contents](#SEC_Contents "Table of contents"){rel="contents"}\]
:::

# Introduction {#Introduction .top}

::: {#SEC_Contents .element-contents}
## Table of Contents {#table-of-contents .contents-heading}

::: contents
-   [1 Overview](#overview){#toc-Overview}
    -   [1.1 Tooling](#Tooling){#toc-Tooling}
    -   [1.2 Interoperability](#Interoperability){#toc-Interoperability}
    -   [1.3 Publishing the
        contract](#Publishing-the-contract){#toc-Publishing-the-contract}
-   [2 Proposal](#proposal){#toc-Proposal}
    -   [2.1 Parameters](#Parameters){#toc-Parameters}
        -   [2.1.1 Deadline](#Deadline){#toc-Deadline}
    -   [2.2 Target vote](#Target-vote){#toc-Target-vote}
    -   [2.3 Options](#Options){#toc-Options}
    -   [2.4 Creating a
        proposal](#Creating-a-proposal){#toc-Creating-a-proposal}
-   [3 Voting](#voting){#toc-Voting}
    -   [3.1 Proposal context](#Proposal-context){#toc-Proposal-context}
    -   [3.2 Options](#Options-1){#toc-Options-1}
    -   [3.3 Cancellation
        votes](#Cancellation-votes){#toc-Cancellation-votes}
    -   [3.4 How to vote](#How-to-vote){#toc-How-to-vote}
-   [4 Results](#results){#toc-Results}
    -   [4.1 Finalizing the
        proposal](#Finalizing-the-proposal){#toc-Finalizing-the-proposal}
        -   [4.1.1 Enhanced
            results](#Enhanced-results){#toc-Enhanced-results}
    -   [4.2 Recovering
        tokens](#Recovering-tokens){#toc-Recovering-tokens}
-   [Appendix A Proposal states](#Proposal-states){#toc-Proposal-states}
:::
:::

------------------------------------------------------------------------

::: {#overview .chapter-level-extent}
::: nav-panel
Next: [Proposal](#proposal){accesskey="n" rel="next"}, Previous:
[Introduction](#Top){accesskey="p" rel="prev"}, Up:
[Introduction](#Top){accesskey="u" rel="up"}  
\[[Contents](#SEC_Contents "Table of contents"){rel="contents"}\]
:::

## 1 Overview {#Overview .chapter}

This smart contract enables voting on proposals using ERC20 tokens.

-   [Tooling](#Tooling){accesskey="1"}
-   [Interoperability](#Interoperability){accesskey="2"}
-   [Publishing the contract](#Publishing-the-contract){accesskey="3"}

::: {#Tooling .section-level-extent}
### 1.1 Tooling {#tooling .section}

Tests and tools are implemented using the
[chainlib-eth](https://pypi.org/project/chainlib-eth){.url} python
package.

To learn more about the individual CLI tools mentioned in this document,
please refer to their individual man pages. The man pages should be
installed as part of the python packages.
:::

::: {#Interoperability .section-level-extent}
### 1.2 Interoperability {#interoperability .section}

The `evm-tokenvote`{.code} contract implements the
`cic-contracts:TokenVote`{.code} interface.
:::

::: {#Publishing-the-contract .section-level-extent}
### 1.3 Publishing the contract {#publishing-the-contract .section}

In python, the smart contract can be published using the
`constructor`{.code} method of the `evm_tokenvote.Voter`{.code} class.

Also, constructor bytecode can be generated on the command-line using
`chainlib-gen`{.code}. Thereafter, `eth-gen`{.code} can be used to
publish the contract through an rpc endpoint:

::: example
``` example-preformatted
# Make sure evm_tokenvote is in your PYTHONPATH
$ chainlib-gen evm_tokenvote create --token_address <token_address> > data.bin
$ eth-gas -p <rpc_url> -y <json_keyfile> [ --passphrase-file <file_with_keyfile_passphrase> ] --data data.bin -i <evm:chain:chain_id:common_name> -s -w 0
```
:::

The `token_address`{.code} argument **MUST** be an existing and valid
`ERC20`{.code} contract.

------------------------------------------------------------------------
:::
:::

::: {#proposal .chapter-level-extent}
::: nav-panel
Next: [Voting](#voting){accesskey="n" rel="next"}, Previous:
[Overview](#overview){accesskey="p" rel="prev"}, Up:
[Introduction](#Top){accesskey="u" rel="up"}  
\[[Contents](#SEC_Contents "Table of contents"){rel="contents"}\]
:::

## 2 Proposal {#Proposal .chapter}

Proposals are created with a 32-byte description.

How the description should be interpreted is up to the client
application.

A proposal may be a binary (yes or no) vote, or define a number of
different options to choose from.

-   [Parameters](#Parameters){accesskey="1"}
-   [Target vote](#Target-vote){accesskey="2"}
-   [Options](#Options){accesskey="3"}
-   [Creating a proposal](#Creating-a-proposal){accesskey="4"}

::: {#Parameters .section-level-extent}
### 2.1 Parameters {#parameters .section}

The arguments required to create a proposal depends on the type of
proposal to create.

-   [Deadline](#Deadline){accesskey="1"}

::: {#Deadline .subsection-level-extent}
#### 2.1.1 Deadline {#deadline .subsection}

The deadline must be defined for all proposals.

It is defined as a period of number of blocks during which votes may be
made.

If a vote has been completed before the deadline is over, the result
will be available immediately.

The contract does not check the sanity of the deadline value. For
example, setting the deadline to `1`{.code} block wait will be useless
as voting will expire immediately.
:::
:::

::: {#Target-vote .section-level-extent}
### 2.2 Target vote {#target-vote .section}

The target vote must be defined for all proposals.

This defines the minimum participation in the vote. It is defined as
parts-per-million of the total supply of tokens.

For example. a value of `500000`{.code} will require 50% of all tokens
in the vote. A value of `1000000`{.code} will require the full supply.
:::

::: {#Options .section-level-extent}
### 2.3 Options {#options .section}

A proposal may define one or more options for voters to choose between.

Options are defined as 32-byte hexadecimal values. As with the
description, it is up to the client application to decide how to
interpret the values.
:::

::: {#Creating-a-proposal .section-level-extent}
### 2.4 Creating a proposal {#creating-a-proposal .section}

To create a proposal without options:

``` verbatim
# solidity:
function propose(bytes32 _description, uint256 _blockWait, uint24 _targetVotePpm) public returns (uint256);

# chainlib-python:
def propose(self, contract_address, sender_address, description, block_deadline, tx_format=TxFormat.JSONRPC, id_generator=None)

# eth-encode CLI:
$ eth-encode --mode tx --signature propose -e <voter_contract_address> -y <keyfile_json> a:<token_address> u:<blocks_until_deadline> u:<target_vote_ppm>
```

To create a proposal with options:

``` verbatim
solidity:
function proposeMulti(bytes32 _description, uint256 _blockWait, uint24 _targetVotePpm) public returns (uint256);

chainlib-python:
def propose(self, contract_address, sender_address, description, block_deadline, options=[<options_hex>, ...])
```

(Unfortunately, `eth-encode`{.code} does not currently support dynamic
array arguments.)

------------------------------------------------------------------------
:::
:::

::: {#voting .chapter-level-extent}
::: nav-panel
Next: [Results](#results){accesskey="n" rel="next"}, Previous:
[Proposal](#proposal){accesskey="p" rel="prev"}, Up:
[Introduction](#Top){accesskey="u" rel="up"}  
\[[Contents](#SEC_Contents "Table of contents"){rel="contents"}\]
:::

## 3 Voting {#Voting .chapter}

Votes are defined in magnitudes of ERC20 tokens.

A vote will transfer ERC20 tokens to the custody of the smart contract
for the duration of the voting.

The smart contract uses the `transferFrom`{.code} method to transfer
tokens. It is the caller's responsibility to make the necessary token
allowance (using `approve`{.code}). Votes with insufficient allowance
will fail.

-   [Proposal context](#Proposal-context){accesskey="1"}
-   [Options](#Options-1){accesskey="2"}
-   [Cancellation votes](#Cancellation-votes){accesskey="3"}
-   [How to vote](#How-to-vote){accesskey="4"}

::: {#Proposal-context .section-level-extent}
### 3.1 Proposal context {#proposal-context .section}

Votes are always cast on the oldest proposal the has not been completed.
:::

::: {#Options-1 .section-level-extent}
### 3.2 Options {#options-1 .section}

If multiple options exist, the token holder may freely distribute votes
between the options.
:::

::: {#Cancellation-votes .section-level-extent}
### 3.3 Cancellation votes {#cancellation-votes .section}

In both proposals with and without options, votes can be cast to cancel
the proposal.

For proposals with no or one option, the *cancel* amounts to a vote
against the proposal.

For proposals with two or more options, the *cancel* amounts to a vote
against proposal and its all options.
:::

::: {#How-to-vote .section-level-extent}
### 3.4 How to vote {#how-to-vote .section}

In each case, make sure the necessary *allowance* has been successfully
executed.

For proposals without options, a simplified method can be called:

``` verbatim
# solidity:
function vote(uint256 _value) public returns (bool);


# chainlib-python:
def vote(self, contract_address, sender_address, value)


# eth-encode CLI:
$ eth-encode --mode tx --signature vote -e <voter_contract_address> -y <keyfile_json> u:<value>
```

For proposal with options, the call is slightly more verbose:

``` verbatim
# solidity:
function voteOption(uint256 _optionIndex, uint256 _value) public returns (bool);


# chainlib-python:
def vote(self, contract_address, sender_address, option=<option_index>, value)


# eth-encode CLI:
$ eth-encode --mode tx --signature voteOption -e <voter_contract_address> -y <keyfile_json> u:<option_index> u:<value>
```

To cast votes for cancellation, the call will be:

``` verbatim
# solidity:
function voteCancel(uint256 _value) public returns (bool);


# chainlib-python:
def vote_cancel(self, contract_address, sender_address, value)


# eth-encode CLI:
$ eth-encode --mode tx --signature voteCancel -e <voter_contract_address> -y <keyfile_json> u:<value>
```

------------------------------------------------------------------------
:::
:::

::: {#results .chapter-level-extent}
::: nav-panel
Previous: [Voting](#voting){accesskey="p" rel="prev"}, Up:
[Introduction](#Top){accesskey="u" rel="up"}  
\[[Contents](#SEC_Contents "Table of contents"){rel="contents"}\]
:::

## 4 Results {#Results .chapter}

A proposal vote is completed if either of the following are true:

-   The deadline has been reached
-   Proposal contains zero or one options, and target participation has
    been reached.
-   Cancellation votes have the majority.

```{=html}
<!-- -->
```
-   [Finalizing the proposal](#Finalizing-the-proposal){accesskey="1"}
-   [Recovering tokens](#Recovering-tokens){accesskey="2"}

::: {#Finalizing-the-proposal .section-level-extent}
### 4.1 Finalizing the proposal {#finalizing-the-proposal .section}

Once a proposal vote has been completed, the proposal must be explicitly
finalized.

Finalization analyzes the results of the vote, and marks the proposal
state accordingly.

It also moves the proposal cursor to activate the next proposal in the
queue.

Finally, it releases the ERC20 tokens used for the vote.

Finalization is performed using the `finalize()`{.code} contract method.
It will fail if used before the proposal vote has been *completed*.

-   [Enhanced results](#Enhanced-results){accesskey="1"}

::: {#Enhanced-results .subsection-level-extent}
#### 4.1.1 Enhanced results {#enhanced-results .subsection}

The optional method `scan(uint256 _proposalIndex, uint256 _count`{.code}
can be called on a completed proposal to further analyze the results of
the vote.

In the current state of the contract, it will iterate the options of the
proposal, and mark the state as `TIED`{.code} if two or more options
have the same amount of votes.

This method may be called any time after proposal has been completed
(even before `finalize()`{.code}. The proposal is identified by the
`_proposalIndex`{.code} parameter, where the index is the order of
addition of the proposal.

The `_count`{.code} parameter limits the amount of options that will be
scanned. A consecutive call will start at the option where the previous
left off.
:::
:::

::: {#Recovering-tokens .section-level-extent}
### 4.2 Recovering tokens {#recovering-tokens .section}

Before a new vote can take place, the ERC20 tokens used in previous
voting must be withdrawn.

Withdrawal is performed using the `withdraw()`{.code} contract method.
It will fail if used before the proposal vote has been *finalized*.
:::
:::

::: {#Proposal-states .appendix-level-extent}
## Appendix A Proposal states {#appendix-a-proposal-states .appendix}

  label                   bit value   description
  ----------------------- ----------- ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
  INIT                    1           Proposal has been initiated. It is used to disambiguate a proposal struct that has not yet been added, due to the ambiguity of the default struct value in solidity.
  `FINAL`{.code}          2           `finalize()`{.code} has been successfully called.
  `SCANNED`{.code}        4           `scan(...)`{.code} has been successfully called for all available options.
  `INSUFFICIENT`{.code}   8           Voting participation did not been the required target vote before the deadline.
  `TIED`{.code}           16          Proposal contains two or more options, and two or more options have received the same amount of votes before the deadline.
  `SUPPLYCHANGE`{.code}   32          The token supply changed between when the proposal was added and voting ended. If supply is protected, this has also `CANCELLED`{.code} the vote.
  `IMMEDIATE`{.code}      64          Voting was completed before the deadline.
  `CANCELLED`{.code}      128         Interpretation depends on context. See below.

Interpreting `CANCELLED`{.code}:

-   With `SUPPLYCHANGE`{.code}, this means that vote has been
    invalidated and should be discarded.
-   If proposal has options, it should be interpreted as that the
    existence of the proposal itself has been *rejected*.
-   With no or one option, it should be interpreted as the proposal has
    been *defeated*.
:::
:::
