## Summary

- 

## Checks

- [ ] I did not add a 10th agent role.
- [ ] I did not model cross-cutting infrastructure as an agent.
- [ ] I did not create domain-specific knowledge tables such as course_chunks or fund_chunks.
- [ ] I did not create feature-local persona storage; user_profiles remains the single persona source.
- [ ] New endpoint/service/repository files include a status comment.
- [ ] Generative skills call rag.retrieve() before LLM generation.
- [ ] Skills call ctx.log_run() before returning.
- [ ] If I changed CLAUDE.md architecture rules, schema, or differences, I updated the matching section.
