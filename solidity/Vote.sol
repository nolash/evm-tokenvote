pragma solidity ^0.8.0;

// Author:	Louis Holbrook <dev@holbrook.no> 0826EDA1702D1E87C6E2875121D2E7BB88C2A746
// SPDX-License-Identifier: AGPL-3.0-or-later
// File-Version: 1
// Description: Voting contract using ERC20 tokens as shares

contract ERC20Vote {
	address public token;

	struct Proposal {
		bytes32 digest;
		bytes32 state;
		uint256 voterMax;
		address proposer;
		uint256 ackBlockDeadline;
		uint256 voteBlockDeadline;
		uint256 voteTargetPpm;
		uint256 scanCursor;
		address []voters;
		bool voterVote;
		bool valid;
		bool active;
		bool ackScanDone;
		bool voteScanDone;
		bool result;
	}
	Proposal emptyProposal;

	mapping ( address => uint256 ) voterState;
	address[] public voters;
	mapping ( uint256 => mapping ( address => uint256 ) ) ack;
	mapping ( uint256 => mapping ( address => uint256 ) ) vote;
	mapping ( uint256 => uint256 ) tally;
	mapping ( uint256 => uint256 ) budget;

	address newVoter;
	//mapping ( address => bytes32 ) newVoterDigest;
	Proposal []proposals;

	uint256 proposalCursor;

	event ProposalAdded(uint256 indexed _proposalIdx, uint256 indexed _ackBlockDeadline, uint256 indexed voteTargetPpm);
	event VoterProposalAdded(uint256 indexed _proposalIdx, uint256 indexed _ackBlockDeadline, uint256 indexed voteTargetPpm, address _voter);
	event VotesAdded(uint256 indexed _proposalIdx, address indexed _voter, uint256 indexed _total, uint256 _delta);
	event VotesWithdrawn(uint256 indexed _proposalIdx, address indexed _voter, uint256 indexed _total, uint256 _delta);

	constructor(address _token) {
		token = _token;
	}

	// bounded processing of all proposals
	// protects the voter population from changing between a vote has been proposed and it has been processed
	function scanProposal(uint256 _count) public returns (bool) {
		uint256 i;
		uint256 delta;
		Proposal storage proposal;

		if (proposalCursor + _count > proposals.length) {
			_count = proposals.length - proposalCursor;
		}

		for (i = proposalCursor; i < proposals.length; i++) {
			proposal = proposals[proposalCursor];
			if (!proposal.active) {
				delta += 1;
			}
		}
		proposalCursor += delta;
		if (proposalCursor == proposals.length) {
			return false;
		}
		return true;
	}

	// bounded processing of acks for a proposal
	// when complete, relevant acks will be committed to the proposal and voting ratification can be possible
	function scanAck(uint256 _proposalIdx, uint256 _count) public returns (bool) {
		Proposal storage proposal;
		uint256 i;

		proposal = getActive(_proposalIdx);

		require(!proposal.ackScanDone);

		if (proposal.scanCursor + _count > voters.length) {
			_count = voters.length - proposal.scanCursor;
		}

		for (i = proposal.scanCursor; i < proposal.scanCursor + _count; i++) {
			address voter;
			if (i == proposal.voterMax) {
				proposal.scanCursor = 0;
				proposal.ackScanDone = true;
				return false;
			}
			voter = voters[i];
			if (voterState[voter] > 0) {
				proposal.voters.push(voter);
			}
			proposal.scanCursor = i;
		}
		return true;
	}

	function scanVote(uint256 _proposalIdx, uint256 _count) public returns (bool) {
		Proposal storage proposal;
		uint256 i;

		proposal = getActive(_proposalIdx);
		require(proposal.voteBlockDeadline <= block.timestamp);
		require(!proposal.voteScanDone);

		if (proposal.scanCursor + _count > proposal.voters.length) {
			_count = proposal.voters.length - proposal.scanCursor;
		}

		for (i = proposal.scanCursor; i < proposal.scanCursor + _count; i++) {
			address voter;
			if (checkProposalBalance(_proposalIdx, voter) == 0) {
				return false;
			}
			if (i == proposal.voters.length) {
				proposal.scanCursor = 0;
				proposal.voteScanDone = true;
				return false;
			}
			voter = voters[i];
			tally[_proposalIdx] += vote[_proposalIdx][voter];
			proposal.scanCursor = i;
		}
		return true;
	}

	// finalize proposal and result
	function ratify(uint256 _proposalIdx) public returns (bool) {
		Proposal storage proposal;
		uint256 tallyPpm;
		uint256 budgetPpm;

		proposal = getActive(_proposalIdx);

		require(proposal.voteScanDone, "ERR_VOTE_SCAN_MISSING");
		if (proposal.voterVote) {
			require(_proposalIdx == proposalCursor, "ERR_PREMATURE_VOTERVOTE");
		}

		tallyPpm = tally[_proposalIdx] * 1000000;
		budgetPpm = budget[_proposalIdx] * 1000000;

		if (tallyPpm / budgetPpm >= proposal.voteTargetPpm) {
			proposal.result = true;
		}
		proposal.active = false;
		return proposal.result;
	}

	// Common code for propose and proposeVoter
	function proposeCore(bytes32 _digest, uint256 _ackBlockDeadline, uint256 _voteBlockDeadline, uint256 _voteTargetPpm) private returns (uint256) {
		require(_ackBlockDeadline > block.number);
		require(_voteBlockDeadline > _ackBlockDeadline);
		require(voters.length > 1);

		Proposal memory proposal;
		uint256 idx;

		proposal.digest = _digest;
		proposal.proposer = msg.sender;
		proposal.voterMax = voters.length - 1;
		proposal.ackBlockDeadline = _ackBlockDeadline;
		proposal.voteBlockDeadline = _voteBlockDeadline;
		proposal.valid = true;
		proposal.active = true;
		proposal.voteTargetPpm = _voteTargetPpm;

		idx = proposals.length;
		proposals.push(proposal);

		return idx;
	}

	// Propose a vote on the subject described by digest.
	function propose(bytes32 _digest, uint256 _ackBlockDeadline, uint256 _voteBlockDeadline, uint256 _voteTargetPpm) public returns (uint256) {
		uint256 r;

		require(newVoter == address(0x0), "ERR_VOTERCHANGE_BLOCK");

		r = proposeCore(_digest, _ackBlockDeadline, _voteBlockDeadline, _voteTargetPpm);
		emit ProposalAdded(r, _ackBlockDeadline, _voteTargetPpm);
		return r;
	}

	// Propose addition of a new voter.
	function proposeVoter(address _voter, uint256 _ackBlockDeadline, uint256 _voteBlockDeadline, uint256 _voteTargetPpm) public returns (uint256) {
		bytes32 voterDigest;
		bytes memory voterDigestMaterial;
		uint256 proposalIdx;

		require(newVoter == address(0x0), "ERR_VOTERCHANGE_BLOCK");

		newVoter = _voter;	
		voterDigestMaterial = abi.encodePacked("bytes", bytes20(_voter));
		voterDigest = sha256(voterDigestMaterial);
		//newVoterDigest[_voter] = voterDigest;

		proposalIdx = proposeCore(voterDigest, _ackBlockDeadline, _voteBlockDeadline, _voteTargetPpm);
		proposals[proposalIdx].voterVote = true;
		emit VoterProposalAdded(proposalIdx, _ackBlockDeadline, _voteTargetPpm, _voter);
		return proposalIdx;
	}

	// returns the active state.
	function getActive(uint256 _proposalIdx) private returns (Proposal storage) {
		Proposal storage proposal;

		proposal = proposals[_proposalIdx];
		if (!proposal.valid) {
			return emptyProposal;
		}
		if (!proposal.active) {
			return emptyProposal;
		}
		if (block.number >= proposal.voteBlockDeadline) {
			proposal.active = false;
		}
		return proposal;
	}

	// register ack for a proposal
	function ackProposal(uint256 _proposalIdx) public returns (bool) {
		Proposal storage proposal;
		uint256 balance;

		proposal = getActive(_proposalIdx);
		require(proposal.active, "ERR_PROPOSAL_INACTIVE");
		require(proposal.ackBlockDeadline < block.number, "ERR_ACK_EXPIRE");

		if (ack[_proposalIdx][msg.sender] > 0) {
			return false;
		}
		balance = getBalance(msg.sender);
		ack[_proposalIdx][msg.sender] = balance;
		budget[_proposalIdx] += balance;
		return true;
	}

	// spend votes on proposal 
	function spendVote(uint256 _proposalIdx, uint256 _amount) public returns (uint256) {
		uint256 balance;
		uint256 usedBalance;
		Proposal storage proposal;

		proposal = getActive(_proposalIdx);
		require(proposal.active, "ERR_PROPOSAL_INACTIVE");
	
		balance = checkProposalBalance(_proposalIdx, msg.sender);
		if (balance == 0) {
			return 0;
		}

		usedBalance = vote[_proposalIdx][msg.sender];
		require(balance - usedBalance >= _amount);
		usedBalance += _amount;
		vote[_proposalIdx][msg.sender] = usedBalance;
		emit VotesAdded(_proposalIdx, msg.sender, usedBalance, _amount);

		return usedBalance;
	}

	// withdraw spent votes on proposal 
	function withdrawVote(uint256 _proposalIdx, uint256 _amount) public returns (uint256) {
		Proposal storage proposal;
		uint256 balance;
		uint256 usedBalance;

		proposal = getActive(_proposalIdx);
		require(proposal.active, "ERR_PROPOSAL_INACTIVE");

		balance = checkProposalBalance(_proposalIdx, msg.sender);
		if (balance == 0) {
			return 0;
		}

		usedBalance = vote[_proposalIdx][msg.sender];
		require(usedBalance >= _amount);
		usedBalance -= _amount;
		vote[_proposalIdx][msg.sender] = usedBalance;
		emit VotesWithdrawn(_proposalIdx, msg.sender, usedBalance, _amount);

		return usedBalance;
	}

	// retrieve token balance from backing erc20 token.
	function getBalance(address _voter) private returns (uint256) {
		bytes memory v;
		bool ok;

		(ok, v) = token.call(abi.encodeWithSignature('balanceOf', _voter));
		require(ok);
		return abi.decode(v, (uint256));
	}

	// invalidate proposal if terms of the vote has changed:
	// * current voter balance does not match voter balance at time of acknowledgement
	function checkProposalBalance(uint256 _proposalIdx, address _voter) private returns (uint256) {
		uint256 balance;
		uint256 origBalance;

		balance = getBalance(_voter);
		origBalance = ack[_proposalIdx][_voter];
		if (balance != origBalance) {
			Proposal storage proposal;
			proposal = proposals[_proposalIdx];
			proposal.valid = false;
			proposal.active = false;
			return 0;
		}
		return balance;
	}
}
