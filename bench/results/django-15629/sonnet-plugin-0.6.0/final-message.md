I ran the sweep. It found nothing else to fix.

- **`db_parameters()` callers:** the base `column_sql` reads collation with `.get("collation")`, and the SQLite schema editor only reads `["type"]`. Neither is affected by the new key.
- **`OneToOneField`:** it inherits `ForeignKey.db_parameters` (checked by calling it), so it gets the collation too. That is the `Address.account` case from your report.
- **`ManyToManyField`:** it returns `type: None`, and its callers use `.get`, so it's safe.
- **`_alter_column_type_sql` overrides:** the only ones outside the base editor are in MySQL, Oracle, PostgreSQL and PostGIS, and I updated all of them.

The unverified part is unchanged: I couldn't run any of this against MySQL, so the generated MySQL SQL is what I expect from the code, not something I've seen. On SQLite the new test returns early, so it checks nothing about the FK fix there.