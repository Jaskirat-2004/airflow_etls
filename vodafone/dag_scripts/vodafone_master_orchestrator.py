"""
PROGRAMMER : JASKIRAT 
INFO : VODAFONE MASTER ORCHESTRATOR
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
    dag_id = "vodafone_master_orchestrator",
    start_date = pendulum.datetime(2026,1,1, tz="Asia/Kolkata"),
    schedule = '0 11 * * *',
    catchup = False,
    tags = ["vodafone", "master"],
    default_args = default_args,
)

def master_orchestrator():

    trigger_etl = TriggerDagRunOperator(
        task_id="trigger_etl",
        trigger_dag_id="vodafone_fact_table_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )

    trigger_roster_upsert = TriggerDagRunOperator(
        task_id="trigger_roster_upsert",
        trigger_dag_id="vodafone_roster_upsert",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )
    
    trigger_attendence = TriggerDagRunOperator(
        task_id="trigger_attendence",
        trigger_dag_id="vodafone_fact_attendence_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )

    # ==================== STARTING TASKS ====================
    trigger_etl
    trigger_roster_upsert >> trigger_attendence

master_orchestrator()
