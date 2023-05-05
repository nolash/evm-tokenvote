pragma solidity ^0.8.0;

// Author:	Louis Holbrook <dev@holbrook.no> 0826EDA1702D1E87C6E2875121D2E7BB88C2A746
// SPDX-License-Identifier: AGPL-3.0-or-later
// File-Version: 1
// Description: Voting contract using ERC20 tokens as shares

// TODO: how to cancel vote prematurely
// TODO: voter registration vote, to enforce 50% per-entity cap rule

contract ERC20Vote {
	uint8 constant STATE_FINAL = 1;
	uint8 constant STATE_SCANNED = 2;
	uint8 constant STATE_INSUFFICIENT = 4;
	uint8 constant STATE_TIED = 8;
	uint8 constant STATE_SUPPLYCHANGE = 16;

	address public token;

	struct Proposal {
		bytes32 description;
		bytes32 []options;
		uint256 []optionVotes;
		uint256 supply;
		uint256 total;
		uint256 blockDeadline;
		uint24 targetVotePpm;
		address proposer;
		uint8 state;
		uint8 scanCursor;
	}

	Proposal[] public proposals;
	address accountsRegistry;

	uint256 public currentProposal;

	mapping ( address => uint256 ) public balanceOf;
	mapping ( address => uint256 ) proposalIdxLock;

	event ProposalAdded(uint256 indexed _blockDeadline, uint256 indexed voteTargetPpm, uint256 indexed _proposalIdx);

	constructor(address _token, address _accountsRegistry) {
		token = _token;
		accountsRegistry = _accountsRegistry;
	}

	// Propose a vote on the subject described by digest.
	function proposeMulti(bytes32 _description, bytes32[] memory _options, uint256 _blockWait, uint24 _targetVotePpm) public returns (uint256) {
		Proposal memory l_proposal;
		uint256 l_proposalIndex;
		uint256 l_blockDeadline;

		require(_options.length < 256, "ERR_TOO_MANY_OPTIONS");
		l_proposal.proposer = msg.sender;
		l_proposal.description = _description;
		l_proposal.options = _options;
		l_proposal.targetVotePpm = _targetVotePpm;
		l_blockDeadline = block.number + _blockWait;
		l_proposal.blockDeadline = l_blockDeadline;
		l_proposalIndex = proposals.length;
		proposals.push(l_proposal);
		l_proposal.supply = checkSupply(proposals[l_proposalIndex]);

		emit ProposalAdded(l_blockDeadline, _targetVotePpm, l_proposalIndex);
		return l_proposalIndex;
	}

	function propose(bytes32 _description, uint256 _blockWait, uint24 _targetVotePpm) public returns (uint256) {
		bytes32[] memory options;

		return proposeMulti(_description, options, _blockWait, _targetVotePpm);
	}

	// reverts on unregistered account if an accounts registry has been added.
	function mustAccount(address _account) private {
		bool r;
		bytes memory v;

		if (accountsRegistry == address(0)) {
			return;
		}
		
		(r, v) = accountsRegistry.call(abi.encodeWithSignature('have(address)', _account));
		require(r, "ERR_REGISTRY");
		r = abi.decode(v, (bool));
		require(r, "ERR_UNAUTH_ACCOUNT");
	}

	// Cast votes on an option by locking ERC20 token in contract.
	// Votes may be divided on several options.
	// If false is returned, proposal has been invalidated.
	function vote(uint256 _optionIndex, uint256 _value) public returns (bool) {
		Proposal storage proposal;
		bool r;
		bytes memory v;

		mustAccount(msg.sender);
		proposal = proposals[currentProposal];
		if (checkSupply(proposal) == 0) {
			return false;
		}
		require(proposal.blockDeadline < block.number, "ERR_DEADLINE");
		if (proposalIdxLock[msg.sender] > 0) {
			require(proposalIdxLock[msg.sender] == currentProposal, "ERR_RECOVER_FIRST");
		}
		require(_optionIndex < proposal.options.length, "ERR_OPTION_INVALID");

		(r, v) = token.call(abi.encodeWithSignature('transferFrom(address,address,uint256)', msg.sender, this, _value));
		require(r, "ERR_TOKEN");
		r = abi.decode(v, (bool));
		require(r, "ERR_TRANSFER");

		proposalIdxLock[msg.sender] = currentProposal;
		balanceOf[msg.sender] += _value;
		proposal.total += _value;
		proposal.optionVotes[_optionIndex] += _value;
		return true;
	}

	// Optionally scan the results for a proposal to make result visible.
	// Returns false as long as there are more options to scan.
	function scan(uint256 _proposalIndex, uint8 _count) public returns (bool) {
		Proposal storage proposal;
		uint8 i;
		uint16 lead;
		uint256 hi;
		uint256 score;
		uint8 c;
		uint8 state;

		proposal = proposals[_proposalIndex];
		require(proposal.blockDeadline <= block.number, "ERR_PREMATURE");
		if (proposal.state & STATE_SCANNED > 0) {
			return false;
		}

		c = proposal.scanCursor;
		if (c + _count > proposal.options.length) {
			_count = uint8(proposal.options.length) - c;
		}

		_count += c;
		state = proposal.state;
		for (i = c; i < _count; i++) {
			score = proposal.optionVotes[i];
			if (score > 0 && score == hi) {
				state |= STATE_TIED;
			} else if (score > hi) {
				hi = score;
				lead = i;
				state &= ~STATE_TIED;
			}
			c += 1;
		}
		proposal.scanCursor = c;
		proposal.state = state;
		if (proposal.scanCursor < proposal.options.length) {
			proposal.state |= STATE_SCANNED;
		}
		return proposal.state & STATE_SCANNED > 0;
	}

	// finalize the results after scanning for winning result.
	// will record and return whether voting participation was insufficient.
	function finalize() public returns (bool) {
		Proposal storage proposal;
		uint256 l_total_m;
		uint256 l_supply_m;

		proposal = proposals[currentProposal];
		require(proposal.state & STATE_FINAL == 0, "ERR_ALREADY_STATE_FINAL");
		require(proposal.state & STATE_SCANNED == 0, "ERR_SCAN_FIRST");
		if (checkSupply(proposal) == 0) {
			return false;
		}
		proposal.state |= STATE_FINAL;
		currentProposal += 1;

		l_total_m = proposal.total * 1000000;
		l_supply_m = proposal.supply * 1000000;

		if (l_supply_m / l_total_m < proposal.targetVotePpm) {
			proposal.state |= STATE_INSUFFICIENT;
			return false;

		}
		return true;
	}

	// should be checked for proposal creation, each recorded vote and finalization.	
	function checkSupply(Proposal storage proposal) private returns (uint256) {
		bool r;
		bytes memory v;
		uint256 l_supply;

		(r, v) = token.call(abi.encodeWithSignature('totalSupply()'));
		require(r, "ERR_TOKEN");
		l_supply = abi.decode(v, (uint256));

		require(l_supply > 0, "ERR_ZERO_SUPPLY");
		if (proposal.supply == 0) {
			proposal.supply = l_supply;
		} else {
			proposal.state |= STATE_SUPPLYCHANGE;
			proposal.state |= STATE_FINAL;
			currentProposal += 1;
			return 0;
		}
		
		return l_supply;
	}

	// Recover tokens from a finished vote or from an active vote before deadline.
	function recover() public returns (uint256) {
		Proposal storage proposal;
		bool r;
		bytes memory v;
		uint256 l_value;

		proposal = proposals[currentProposal];

		l_value = balanceOf[msg.sender];
		if (proposalIdxLock[msg.sender] == currentProposal) {
			if (proposal.blockDeadline <= block.number) {
				require(proposal.state & STATE_FINAL == 0, "ERR_PREMATURE");
			} else {
				proposal.total -= l_value;
			}
		}

		balanceOf[msg.sender] = 0;
		proposalIdxLock[msg.sender] = 0;
		(r, v) = token.call(abi.encodeWithSignature('transfer(address,uint256)', msg.sender, l_value));
		require(r, "ERR_TOKEN");
		r = abi.decode(v, (bool));
		require(r, "ERR_TRANSFER");

		return l_value;
	}
}
