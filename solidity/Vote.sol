pragma solidity ^0.8.0;

// Author:	Louis Holbrook <dev@holbrook.no> 0826EDA1702D1E87C6E2875121D2E7BB88C2A746
// SPDX-License-Identifier: AGPL-3.0-or-later
// File-Version: 1
// Description: Voting contract using ERC20 tokens as shares

contract ERC20Vote {
	address public token;

	struct Proposal {
		bytes32 digest;
		uint256 voterMax;
		address proposer;
		bool voterVote;
		bool valid;
		bool active;
	}

	mapping ( address => uint256 ) voterState;
	address[] public voters;
	mapping ( bytes32 => mapping ( address => uint256 ) ) ack;
	mapping ( bytes32 => mapping ( address => uint256 ) ) vote;

	mapping ( address => bytes32 ) newVoterDigest;
	Proposal []proposals;

	event Vote(uint256 indexed _proposalIdx, address indexed _voter, uint256 indexed _total, uint256 _delta);

	constructor(address _token) {
		token = _token;
	}

	function propose(bytes32 _digest) public returns (uint256) {
		require(voters.length > 1);

		Proposal memory proposal;
		uint256 idx;

		proposal.digest = _digest;
		proposal.proposer = msg.sender;
		proposal.voterMax = voters.length - 1;
		proposal.valid = true;
		proposal.active = true;

		idx = proposals.length;
		proposals.push(proposal);
		return idx;
	}

	function proposeVoter(address _voter) public returns (uint256) {
		bytes32 voterDigest;
		bytes memory voterDigestMaterial;
		uint256 proposalIdx;
	
		voterDigestMaterial = abi.encodePacked("bytes", bytes20(_voter));
		voterDigest = sha256(voterDigestMaterial);
		newVoterDigest[_voter] = voterDigest;

		proposalIdx = propose(voterDigest);
		proposals[proposalIdx].voterVote = true;
		return proposalIdx;
	}

	function ackVote(uint256 _proposalIdx) public returns (bool) {
		Proposal storage proposal;
		uint256 balance;

		proposal = proposals[_proposalIdx];

		if (ack[proposal.digest][msg.sender] > 0) {
			return false;
		}
		balance = getBalance(msg.sender);
		ack[proposal.digest][msg.sender] = balance;
		return true;
	}

	function spendVote(uint256 _proposalIdx, uint256 _amount) public returns (uint256) {
		uint256 balance;
		uint256 usedBalance;
		uint256 origBalance;
		Proposal storage proposal;

		proposal = getAsActive(_proposalIdx);
		
		balance = getBalance(msg.sender);
		
		origBalance = ack[proposal.digest][msg.sender];
		if (origBalance != balance) {
			proposal.valid = false;
			proposal.active = false;
			return 0;
		}
		
		usedBalance = vote[proposal.digest][msg.sender];
		require(usedBalance >= _amount);
		usedBalance += _amount;
		vote[proposal.digest][msg.sender] = usedBalance;
		emit Vote(_proposalIdx, msg.sender, usedBalance, _amount);

		return usedBalance;
	}

	function getBalance(address _voter) private returns (uint256) {
		bytes memory v;
		bool ok;

		(ok, v) = token.call(abi.encodeWithSignature('balanceOf', _voter));
		require(ok);
		return abi.decode(v, (uint256));
	}

	function getAsActive(uint256 _digestIdx) private view returns (Proposal storage) {
		Proposal storage proposal;

		proposal = proposals[_digestIdx];
		require(proposal.active);
		return proposal;
	}
}
