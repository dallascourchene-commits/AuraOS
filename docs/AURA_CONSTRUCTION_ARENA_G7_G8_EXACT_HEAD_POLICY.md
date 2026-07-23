# Construction Arena G7–G8 Exact-Head Policy

The final pull request must:

1. check out `github.event.pull_request.head.sha` from the pull-request head repository;
2. verify `git rev-parse HEAD` equals that expected SHA before running tests;
3. compile all review evidence against that same immutable head;
4. regenerate navigation only after source and tests stabilize;
5. rerun final checks after every review repair;
6. merge with the expected head SHA so a moved branch is rejected;
7. retain human authorization as the only merge authority.
