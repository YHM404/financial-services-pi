---
description: Build IRR/MOIC sensitivity tables
argument-hint: "[company or deal parameters]"
---

Load the `returns-analysis` skill and model PE returns with sensitivity across entry multiple, leverage, exit multiple, and growth scenarios.

If deal parameters are provided, use them. Otherwise ask the user for entry EBITDA, valuation, and financing assumptions.

## User request from pi command arguments

$ARGUMENTS

If the request above is blank or missing required inputs, ask concise follow-up questions before proceeding.
