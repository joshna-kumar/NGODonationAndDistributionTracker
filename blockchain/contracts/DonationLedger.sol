// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DonationLedger {
    struct DistributionRecord {
        uint256 distributionId;
        uint256 donationId;
        uint256 beneficiaryId;
        uint256 amount;
        uint256 timestamp;
        address sender;
    }

    mapping(uint256 => DistributionRecord) private records;
    mapping(uint256 => bool) public recorded;

    event DistributionRecorded(
        uint256 indexed distributionId,
        uint256 indexed donationId,
        uint256 indexed beneficiaryId,
        uint256 amount,
        uint256 timestamp,
        address sender
    );

    function recordDistribution(
        uint256 distributionId,
        uint256 donationId,
        uint256 beneficiaryId,
        uint256 amount
    ) external {
        require(!recorded[distributionId], "Distribution already recorded");

        records[distributionId] = DistributionRecord(
            distributionId,
            donationId,
            beneficiaryId,
            amount,
            block.timestamp,
            msg.sender
        );
        recorded[distributionId] = true;

        emit DistributionRecorded(
            distributionId,
            donationId,
            beneficiaryId,
            amount,
            block.timestamp,
            msg.sender
        );
    }

    function getDistribution(uint256 distributionId)
        external
        view
        returns (DistributionRecord memory)
    {
        require(recorded[distributionId], "Distribution not found");
        return records[distributionId];
    }
}
