"""Provider-independent AI layer.

Provider kinds are always reported explicitly so mock or deterministic output
can never be presented as real AI output:
  external — a real call to an AI service (anthropic, claude-code)
  local    — deterministic factory analysis (no model involved)
  mock     — scripted responses for tests only
  none     — not configured
"""
