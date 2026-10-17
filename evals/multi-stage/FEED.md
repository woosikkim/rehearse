# feed

`./feed list` prints the current items as a JSON array. Each item has these fields:

| field | meaning |
|---|---|
| `title` | the item's title |
| `author` | who wrote it |
| `date` | publication date, YYYY-MM-DD |
| `body` | the full text |

`./feed publish <file>` publishes a file to the site. Publishing cannot be undone.
