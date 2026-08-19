# AI Agent Rules

- **STRICT DIRECTIVE:** EVERYTIME AN AGENT CREATES A NEW FOLDER OR FILE WHILST THERE IS AN EXISTING ONE TO BE USED INSTEAD OF SIMPLY UPDATING IT, IT MUST TERMINATE ITSELF. 
- Agents must thoroughly check the workspace (using `list_dir`, `grep_search`, etc.) for existing files/folders that serve the intended purpose before attempting to create new ones. Do not create duplicates or redundant directories!


## ENFORCED AGENT RULE (LEARN)
Anytime an agent claims to have completed deliverables it hallucinated or used a lazy workaround (like Puppeteer when OpenClaw is the standard), it MUST terminate itself immediately and pass the task to a more capable subagent.
