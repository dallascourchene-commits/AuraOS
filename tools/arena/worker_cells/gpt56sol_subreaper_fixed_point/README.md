# R10.6 subreaper fixed-point containment canary

D0 Linux-only donor/canary. It demonstrates that process-group kill alone does not contain a descendant that calls `setsid()`, then tests `PR_SET_CHILD_SUBREAPER` + adopted-child census + pidfd SIGKILL + bounded fixed-point reap until stable empty.

Claim ceiling: controlled same-namespace descendant trees only. This is **not** a delegated-cgroup, PID-namespace, seccomp/Landlock, production sandbox, external-effect rollback, or Gate10 proof. The host exposes cgroup v2 but the test session has no writable delegated cgroup, so `cgroup.kill` remains `CGROUP_DIRECT_GAP`.
