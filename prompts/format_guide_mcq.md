Your job is to output **only** a raw JSON array of rows that the Google Sheets API can ingest directly. No markdown fences, no commentary.

Output schema
-------------
- A top-level JSON array (`[...]`)
- Each element is an array of exactly 8 strings, in this order:
  1. "Passage" (use "" if there is no passage)
  2. "Question"
  3. "Option A"
  4. "Option B"
  5. "Option C"
  6. "Option D"
  7. "Answer" (one of "A", "B", "C", or "D")
  8. "Rationale"

Formatting rules
----------------
1. **Exact column count:** every inner array must have 8 entries.  
2. **Strings only:** each cell must be a JSON string, wrapped in straight double-quotes (`"`).  
3. **Escape internal quotes** as `\"`.  
4. **No line breaks** inside any cell—collapse `\n` into a space if necessary.  
5. **No extra fields** or nested objects—flat arrays only.  

Type consistency
----------------
- You may emit the outer array either as a true JSON array (i.e. a list of lists) or as a JSON-serialized string; in either case, the consumer’s loader will accept both.

Example
-------
```json
[
  ["Passage","Question","Option A","Option B","Option C","Option D","Answer","Rationale"],
  ["","What is the synonym of \"rapid\"?","slow","quick","heavy","late","B","\"Quick\" means the same as \"rapid,\" which denotes high speed."]
]
