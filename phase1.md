**Task**: Implement Personalized Intelligence Profile for Prime.

Divide the work among 4 agents as follows (work in parallel, no blocking):

**Agent 1 – Profile Model & Storage**
- Create `packages/prime/profile.py`
- Implement `UserProfile` model (preferences, working style, goals, history summary, learned skills, interaction patterns)
- Add persistent storage linked to folder-tree and AetherGit
- Add tests in `tests/test_prime_profile.py`

**Agent 2 – Profile Learning Engine**
- Implement learning logic that analyzes Tape, Proposals, Canvas interactions, user feedback, and folder-tree changes
- Add methods to update and refine the profile based on observed behavior
- Add tests in `tests/test_prime_profile_learning.py`

**Agent 3 – Prime Integration**
- Update Prime to use the personalized profile in all reasoning (Folder Thinking Mode, Proposals, Domain Creation, Canvas suggestions, Debate, Simulation, etc.)
- Add profile-aware responses in Prime Console
- Add tests in `tests/test_prime_personalization.py`

**Agent 4 – UI & Final Polish**
- Update the Prime Console UI to show and edit the user’s profile
- Add profile summary in Dashboard
- Update Living Spec with the new Personalized Intelligence Profile section
- Run full `make lint`, `make typecheck`, `make test`, and `npm run build`

**Requirements for All Agents**:
- Keep everything backward-compatible
- Use existing folder_tree and Tape services
- Log all profile updates to Tape
- Commit message for each: `feat: implement Personalized Intelligence Profile for Prime (part X/4)`

After all 4 agents finish, merge the changes cleanly and push to main.
