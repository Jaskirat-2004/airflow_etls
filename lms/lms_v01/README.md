# lms_v01 — v0 + v1 consolidated into one folder

**2026-08-24/25.** The old `lms_v0/` (5 files) and `lms_v1/` (8 files, two nested subfolders) were merged
into this single flat folder. **All 10 non-empty code files are kept, byte-for-byte.**

`lms_v2/` is the live generation and was not touched.

## What changed

**Nothing was rewritten.** Files are identical to the originals; only the names carry a `_v0` / `_v1`
suffix, because the two generations had five same-named files that differ:

| File here | Came from |
|---|---|
| `config_v0.py` | `lms_v0/config.py` |
| `config_v1.py` | `lms_v1/final/config.py` |
| `lms_etl_v0.py` | `lms_v0/lms_etl.py` |
| `lms_etl_v1.py` | `lms_v1/final/lms_etl.py` |
| `lms_etl_typecasted_v0.py` | `lms_v0/lms_etl_typecasted.py` |
| `lms_fact_tables_v0.py` | `lms_v0/lms_fact_tables.py` |
| `lms_fact_tables_v1.py` | `lms_v1/final/lms_fact_tables.py` |
| `table_creation_single_task_v0.py` | `lms_v0/table_creation_single_task.py` |
| `etl_v1_current_working.py` | `lms_v1/current_working/etl.py` |
| `table_create_v1_current_working.py` | `lms_v1/current_working/table_create.py` |

**Removed — 3 files, all 0 bytes** (empty, nothing to keep): `lms_v1/final/lms_etl_typecasted.py`,
`lms_v1/final/lms_incremental_etl.py`, `lms_v1/final/table_creation_single_task.py`.

**Added:** `fact_certificate_awards.sql` — see below.

## ⛔ `.airflowignore` — read this before deploying

These files still declare live `dag_id`s, and they **collide**:

- `lms_etl` — declared in **4** files (`lms_etl_v0`, `lms_etl_v1`, `lms_etl_typecasted_v0`, `etl_v1_current_working`)
- `lms_create_tables` — **2** (`table_creation_single_task_v0`, `table_create_v1_current_working`)
- `lms_facts` (v0) and `lms_fact_tables` (v1) — one each

Airflow keeps whichever it parsed **last, non-deterministically**. So two guards are in place:
`.airflowignore` in this folder (pattern `.*`), and `lms_v01` listed in `DAGS\lms\.airflowignore`.
**Do not remove them** while these files sit anywhere under the dags folder.

## `fact_certificate_awards.sql` — extracted, because nothing else builds it

Pulled out of `lms_fact_tables_v1.py` (L266-318 query, L351-375 DDL) into a standalone file, since it's
the one thing here that `lms_v2` has **no** successor for. The source `.py` is still in this folder —
the `.sql` is a convenience copy with the findings attached, not a replacement.

Verified live 2026-08-24 — it will **not** run as-is:

1. **No source data.** `Certificate` = **0 rows**, `CertificateTolanguageMaster` = **0 rows** across all
   10 tenants in db4. Only `languageMaster` has data (32 rows).
2. **Two columns aren't ingested.** It needs `Certificate."type"` and `courses."certificateId"` —
   neither is in the live landing tables. The second is **fatal**: it's the certificate→course join key.
3. **`client_name` → `tenant_name`** (6 places); v2 standardised on the latter.
4. `cert.status = 1` assumes an integer; v2 ingests `Certificate.status` with no cast — check the type.

Design note: `Certificate` **does** carry `userId`, so a direct certificate×user grain might drop the
`courses` + `CourseProgress` hop entirely. Decide that before writing SQL.

## Context: how these relate to lms_v2

Useful when deciding what to trim from this folder later — `lms_v2` already supersedes most of it:

- v0/v1 built `lms.fact_course_completion` and `lms.fact_certificate_awards`. **Neither exists** in live
  ClickHouse `lms` (db5 holds 6 tables: the 4 v2 facts + 2 `_merged`), and no Superset dataset
  references them.
- `fact_course_completion` is the ancestor of `lms_fact_user_x_lesson`: v1 used **3** window frames for
  the completion rollup, `lms_v2/config/fact_config.py` uses **5** (`w1`–`w5`).
- The epoch-sentinel guard (`'1970-01-01 05:30:00'`) from v0 is present in **all four** v2 fact queries.

So the practical value of this folder is history + the certificate design. Trim further if you want —
the full original backup (all 13 files, including the 3 empty ones) is zipped at
`…\Temp\claude\C--Users-8242K-superset-mcp\<session>\scratchpad\lms_v0_v1_backup_20260824.zip`
(**session-temporary** — move it if you want it kept). Don't commit it to `superset-mcp` (public upstream).
