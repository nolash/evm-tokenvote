SOLC = /usr/bin/solc

all:
	$(SOLC) --bin Voter.sol --evm-version byzantium | awk 'NR>3' > Voter.bin
	$(SOLC) --abi Voter.sol --evm-version byzantium | awk 'NR>3' > Voter.json
	$(SOLC) --metadata Voter.sol --evm-version byzantium | awk 'NR>3' > Voter.metadata.json
	truncate -s -1 Voter.bin

install: all
	cp -v *.json ../python/evm_tokenvote/data/
	cp -v *.bin ../python/evm_tokenvote/data/

