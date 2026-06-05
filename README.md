# Airflow ETL Pipelines

A collection of production Apache Airflow pipelines that ingest data from production application databases into analytics warehouses, then model it into fact tables for reporting. Built with the TaskFlow API on a shared design philosophy: **incremental, idempotent, watermark-driven loads** that are safe to re-run and deliberately gentle on the production source databases.

## Tech stack

- **Orchestration:** Apache Airflow (TaskFlow `@dag`/`@task`, dynamic task mapping, `TriggerDagRunOperator` orchestration)
- **Languages:** Python, SQL
- **Sources:** PostgreSQL (production application databases)
- **Warehouses:** ClickHouse (LMS, Traya), PostgreSQL data lake (LeapMax)
- **Connections & secrets:** all database credentials are resolved at runtime through Airflow Connections (`PostgresHook`, ClickHouse `Client` built from a stored connection) — not hardcoded in the DAGs.

## Repository layout

```
.
├── traya/      # Call-centre / CRM fact pipeline  → ClickHouse
├── lms/        # Learning Management System analytics → ClickHouse
├── leapmax/    # Agent-activity / workforce ingestion → PostgreSQL lake
├── maxicus/    # ⚠ earlier draft of the LeapMax pipeline — superseded (see note)
└── test/       # connection / scratch experiments
```

---

## `leapmax/` — agent-activity ingestion (multi-tenant)

Ingests workforce-monitoring data (agent activity, screen events, break logs, etc.) from a production application database into a PostgreSQL analytics lake, across multiple tenants.

- **Source → destination:** production app DB (`prod_ksoft_leap`) → PostgreSQL lake (`DI-POSTGRES`, db `leapmax`)
- **Tenants:** processed **sequentially**, not in parallel — a deliberate choice to avoid putting concurrent load on the production source.
- **Load strategies per table:** time-series tables (e.g. `activity`) load **incrementally**; smaller dimension tables use full refresh.
- **Watermarking:** a `leap_tracking` table records `last_run` / `last_row_id` per (table, tenant), so each run resumes from where the last one stopped and re-runs are safe.
- **Connection resilience:** the production source drops idle connections *between* batches. Handled with per-window connection handling and retries so a dropped connection recovers instead of failing the whole run.

```
leapmax/
├── config.py                    # connections, tenant list, per-table load config
├── create_table.py              # destination DDL
├── simple_etl.py                # production ETL (time-series incremental + full refresh)
├── new_etl(activity_update).py  # activity-update variant
└── overkill_etl.py              # exploratory implementation — NOT in production, kept for reference
```

---

## `lms/` — Learning Management System analytics

Transforms LMS operational data into ClickHouse fact tables for reporting on learning activity, assessments, certificates, and agent progress.

- **Destination:** ClickHouse
- **Fact tables:** agent journey, quiz assigned, quiz submitted, user × lesson, plus course/assessment/certificate facts.
- **Orchestration:** `lms_master_orchestrator` chains the stages in order — raw ETL → fact-table build → merged fact tables — using `TriggerDagRunOperator` with `wait_for_completion`.
- **Incremental:** watermark-driven loads consistent with the other pipelines.

**Version note:** `lms_v2/` is the current, most-developed version. `lms_v1/` and `final/` are earlier iterations kept for history — `lms_v2/` is the one to read.

```
lms/lms_v2/
├── lms_master_orchestrator.py   # top-level orchestrator (ETL → facts → merged facts)
├── lms_etl_dynamic.py           # source → ClickHouse, dynamically mapped
├── lms_fact_table_etl.py        # fact-table builds
├── lms_fact_*_merged.py         # merged/derived fact tables
├── config/                      # config + fact_config
├── fact_table_query/*.sql       # fact-table SQL transforms
├── sql_queries/*.sql            # source extraction queries
└── utils/basic_utils.py
```

---

## `traya/` — CRM / call-centre fact pipeline

Builds analytical fact tables from raw call-centre operational data (call history, agent sessions, calling KPIs).

- **Destination:** ClickHouse fact tables (e.g. `traya_fact_crm_report`)
- **Incremental:** loads bounded by a high-water-mark (`report_date > last_processed AND <= high_water_mark`), so each run processes only new data.
- **Dynamic task mapping:** each fact table is processed as its own mapped task via `.expand()`, with `map_index_template` giving each instance a readable name in the Airflow UI instead of `0, 1, 2`.
- **Config-driven:** fact definitions (query + DDL + source tables) live in `config/fact_table_config.py`, so adding a fact table is a config change rather than new DAG code.

```
traya/
├── config/fact_table_config.py        # fact-table definitions
├── create_table_commands/*.sql        # raw-table DDL
├── dag_scripts/
│   ├── traya_fact_table_creation.py   # creates destination fact tables
│   └── traya_fact_table_etl.py        # incremental fact ETL (dynamic task mapping)
├── fact_table_sql/                    # fact-table SQL transforms
└── util/traya_util_.py                # shared helpers (connections, inserts)
```

---

## `maxicus/` — ⚠ superseded

This is an **earlier draft of the LeapMax pipeline**, not a separate project: same source (`prod_ksoft_leap`), same destination (`DI-POSTGRES`), same tenants, same `leap_tracking` watermark table. It contains three near-identical copies of the same ETL (`maxicus_etl.py`, `FINAL_WALI.py`, `EETTLL.py`). The current implementation lives in `leapmax/`. **Recommend deleting this folder** — it's kept only until you've confirmed nothing references it.

---

## Common patterns across all pipelines

- **Incremental & idempotent.** Every pipeline tracks a watermark (timestamp or row id) and processes only new data, so DAGs are safe to re-run and backfill.
- **Config-driven tables.** Table definitions live in config; the DAG logic stays generic so new tables are added declaratively.
- **Source-database protection.** Sequential processing, batched reads, and connection handling are all designed around not destabilising the production source.
- **DDL separated from ETL.** Table creation is split from data loading so schema changes and loads can be reasoned about independently.

## Notes

- Credentials are managed through Airflow Connections, not stored in this repo.
- Some folders contain multiple iterations of the same pipeline as it evolved; the README flags the current version in each case.
