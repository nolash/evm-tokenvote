pragma solidity ^0.8.0;

// Author:	Louis Holbrook <dev@holbrook.no> 0826EDA1702D1E87C6E2875121D2E7BB88C2A746
// SPDX-License-Identifier: AGPL-3.0-or-later
// File-Version: 1
// Description: Voting contract using ERC20 tokens as shares

contract ERC20Vote {
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
		int16 result;
		uint8 scanCursor;
		bool active;
	}

	Proposal[] public proposals;

	uint256 public currentProposal;

	mapping ( address => uint256 ) public balanceOf;
	mapping ( address => uint256 ) proposalIdxLock;

	event ProposalAdded(uint256 indexed _blockDeadline, uint256 indexed voteTargetPpm, uint256 indexed _proposalIdx);

	constructor(address _token) {
		token = _token;
	}

	function proposeCore(bytes32 _description, bytes32[] calldata _options, uint256 _blockDeadline, uint24 _targetVotePpm) private returns (uint256) {
		Proposal memory l_proposal;
		uint256 l_proposalIndex;

		require(_options.length < 256, "ERR_TOO_MANY_OPTIONS");
		l_proposal.proposer = msg.sender;
		l_proposal.description = _description;
		l_proposal.options = _options;
		l_proposal.targetVotePpm = _targetVotePpm;
		l_proposal.blockDeadline = _blockDeadline;
		l_proposalIndex = proposals.length;
		proposals.push(l_proposal);
		l_proposal.supply = checkSupply(proposals[l_proposalIndex]);
		return l_proposalIndex;
	}

	// Propose a vote on the subject described by digest.
	function propose(bytes32 _description, bytes32[] calldata _options, uint256 _blockDeadline, uint24 _targetVotePpm) public returns (uint256) {
		uint256 r;

		r = proposeCore(_description, _options, _blockDeadline, _targetVotePpm);
		emit ProposalAdded(_blockDeadline, _targetVotePpm, r);
		return r;
	}

	// Cast votes on an option by locking ERC20 token in contract.
	// Votes may be divided on several options.
	function vote(uint256 _optionIndex, uint256 _value) public {
		Proposal storage proposal;
		bool r;
		bytes memory v;

		proposal = proposals[currentProposal];
		require(proposal.blockDeadline < block.number, "ERR_DEADLINE");
		require(proposal.active, "ERR_PROPOSAL_INACTIVE");
		if (proposalIdxLock[msg.sender] > 0) {
			require(proposalIdxLock[msg.sender] == currentProposal, "ERR_RECOVER_FIRST");
		}
		require(_optionIndex < proposal.options.length, "ERR_OPTION_INVALID");

		(r, v) = token.call(abi.encodeWithSignature('transferFrom', msg.sender, this, _value));
		require(r, "ERR_TOKEN");
		r = abi.decode(v, (bool));
		require(r, "ERR_TRANSFER");

		proposalIdxLock[msg.sender] = currentProposal;
		balanceOf[msg.sender] += _value;
		proposal.total += _value;
		proposal.optionVotes[_optionIndex] += _value;
	}

	function scan(uint8 _count) public returns (int16) {
		Proposal storage proposal;
		uint8 i;
		uint16 lead;
		uint256 hi;
		uint256 score;
		uint8 c;

		proposal = proposals[currentProposal];
		require(proposal.active, "ERR_INACTIVE");
		require(proposal.blockDeadline <= block.number, "ERR_PREMATURE");
		require(proposal.scanCursor < proposal.options.length, "ERR_ALREADY_SCANNED");
		c = proposal.scanCursor;
		if (c + _count > proposal.options.length) {
			_count = uint8(proposal.options.length) - c;
		}

		_count += c;
		for (i = c; i < _count; i++) {
			score = proposal.optionVotes[i];
			if (score > 0 && score == hi) {
				proposal.result = -2;
			} else if (score > hi) {
				hi = score;
				lead = i;
				proposal.result = int16(lead);
			}
			c += 1;
		}
		if (c == proposal.options.length) {
			proposal.active = false;
		}
		proposal.scanCursor = c;
		return proposal.result;
	}

	function finalize() public returns (bool) {
		Proposal storage proposal;
		uint256 l_total_m;
		uint256 l_supply_m;

		proposal = proposals[currentProposal];
		require(proposal.result != 0, "ERR_SCAN_FIRST");
		require(proposal.active, "ERR_INACTIVE");

		if (proposal.result < 0) {
			return false;
		}

		l_total_m = proposal.total * 1000000;
		l_supply_m = proposal.supply * 1000000;

		if (l_supply_m / l_total_m < proposal.targetVotePpm) {
			proposal.result = -3;
			return false;

		}
		return true;
	}
	
	function checkSupply(Proposal storage proposal) private returns (uint256) {
		bool r;
		bytes memory v;
		uint256 l_supply;

		(r, v) = token.call(abi.encodeWithSignature('totalSupply'));
		require(r, "ERR_TOKEN");
		l_supply = abi.decode(v, (uint256));

		require(l_supply > 0, "ERR_ZERO_SUPPLY");
		if (proposal.supply == 0) {
			proposal.supply = l_supply;
		} else {
			proposal.active = false;
			proposal.result = -1;
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
		checkSupply(proposal);

		l_value = balanceOf[msg.sender];
		if (proposalIdxLock[msg.sender] == currentProposal) {
			if (proposal.blockDeadline <= block.number) {
				require(proposal.result == 0, "ERR_PREMATURE");
			} else {
				proposal.total -= l_value;
			}
		}

		balanceOf[msg.sender] = 0;
		proposalIdxLock[msg.sender] = 0;
		(r, v) = token.call(abi.encodeWithSignature('transfer', msg.sender, l_value));
		require(r, "ERR_TOKEN");
		r = abi.decode(v, (bool));
		require(r, "ERR_TRANSFER");

		return l_value;
	}
}
