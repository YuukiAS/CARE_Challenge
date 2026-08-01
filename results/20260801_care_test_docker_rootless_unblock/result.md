# Result

ROOTLESS_DOCKER_PREREQUISITE_BLOCKED

The controller performed the required rootless prerequisites audit, downloaded and inspected the official rootless Docker installer, and stopped before installation because the current user lacks required subordinate uid/gid ranges. This supersedes the previous docker-missing-only blocked packet with a more specific host prerequisite blocker.
