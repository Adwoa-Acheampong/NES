---
name: council
description: Use The Council MCP for multi-advisor review, business/legal/technical critique, due diligence, and brief or strategy revision workflows.
---

# The Council

Use this skill when the user asks to convene the council, use the Council MCP, run a business/legal/technical council, perform due diligence, audit a brief, or revise a document using multiple advisor perspectives.

## Local Bundle

- Root: `C:\Users\lenovo\OneDrive\Desktop\The-Council`
- MCP server: `C:\Users\lenovo\OneDrive\Desktop\The-Council\council_mcp_server.py`
- Brief review protocol: `C:\Users\lenovo\OneDrive\Desktop\The-Council\council_brief_review.md`
- Native council skills: `C:\Users\lenovo\OneDrive\Desktop\The-Council\skills`
- Council configs: `C:\Users\lenovo\OneDrive\Desktop\The-Council\councils`

## Preferred Workflow

1. Use the `council` MCP server when its tools are available.
2. Call `list_councils` to see available panels.
3. Call `load_skills` for the relevant domain when reference material is needed.
4. Call `convene_council` for parallel advisor review.
5. Synthesize the advisors' output into concrete edits or a prioritized action list.

The Council includes Claude Sonnet 4.6 as `Narrative Architect`, a seventh external advisor focused on investor-ready narrative, document structure, and exact revision moves. It runs through OpenRouter as `anthropic/claude-sonnet-4.6` and may require OpenRouter credits.

## Council Selection

- `business`, composition `audit`: financial, operational, market, governance, risk, and investor-readiness audit.
- `business`, composition `advisory`: startup strategy, product-market fit, growth, fundraising, operations, and founder decisions.
- `business`, composition `due_diligence`: investor-style diligence and deal-risk review.
- `legal`: contract, regulatory, IP, and corporate-structure review.
- `technical`: architecture, security, DevOps, and testing review.
- `default`: broad first-principles, expansion, challenge, research, contrarian, and outsider review.

## Brief Editing

For business briefs, first read the target brief and `council_brief_review.md`. Use the business council unless the user asks for legal or technical review. Treat council output as advisory: verify claims, preserve the user's intended voice, and make focused document edits rather than wholesale rewrites unless requested.

## Fallback

If the MCP tools are not loaded in the current Codex session, use the standalone runner from the bundle:

```powershell
python "C:\Users\lenovo\OneDrive\Desktop\The-Council\council.py" --council business --composition audit "Question or document excerpt"
```

Do not copy API keys from `council_config.json` into Codex config or chat output.
