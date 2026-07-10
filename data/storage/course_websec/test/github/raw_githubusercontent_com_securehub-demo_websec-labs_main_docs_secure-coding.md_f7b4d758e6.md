Secure Coding Checklist
安全编码 checklist starts from threat modeling, input validation,
output encoding, authentication, authorization and dependency review.
Every GitHub README or docs page should keep a clear fix workflow:
issue, commit, regression test, evidence note and residual risk.
For Web security labs, SQL injection uses parameterized queries,
XSS uses context-aware output encoding, CSRF uses tokens and SameSite,
and upload handlers isolate object_key storage outside the web root.