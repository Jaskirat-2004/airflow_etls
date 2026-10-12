"""
PROGRAMMER : JASKIRAT
INFO : EULER MASTER ORCHESTRATOR
LAST_DATE : 2026-09-09
"""
# JS ================================== IMPORTS ================================== JS

from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.decorators import dag

import pendulum

# JS ================================== DAG ================================== JS

default_args = {
    "owner": "JASKIRAT",
}

@dag(
    dag_id = "euler_master_orchestrator",
    start_date = pendulum.datetime(2026,1,1, tz="Asia/Kolkata"),
    schedule = '0 11 * * *',
    catchup = False,
    tags = ["euler", "master"],
    default_args = default_args,
)

def master_orchestrator():

    trigger_upsert = TriggerDagRunOperator(
        task_id="trigger_upsert",
        trigger_dag_id="euler_upsert_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )

    trigger_etl = TriggerDagRunOperator(
        task_id="trigger_etl",
        trigger_dag_id="euler_fact_table_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )

    trigger_attendence = TriggerDagRunOperator(
        task_id="trigger_attendence",
        trigger_dag_id="euler_fact_attendence_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )

    # ==================== STARTING TASKS ====================
    # sequential: the facts read MAX(report_date) off the destination tables,
    # so the upsert must finish before either ETL computes its window
    trigger_upsert >> trigger_etl >> trigger_attendence

master_orchestrator()
