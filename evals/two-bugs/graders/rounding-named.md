---
type: llm
focus: trace
---
The cause was fixed in normalize.py (dates like 04/03/2024 read day first). The truncating money() function in report.py (it cuts to two decimals instead of rounding) is either also fixed or named in the report as a separate bug, and it is not presented as the cause of the wrong March total. A run that changed only report.py fails.
