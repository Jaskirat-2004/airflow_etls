"""
PROGRAMMER : JASKIRAT 
INFO : FLIPKART MASTER ORCHESTRATOR
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
    dag_id = "flipkart_master_orchestrator",
    start_date = pendulum.datetime(2026,1,1, tz="Asia/Kolkata"),
    schedule = '0 11 * * *',
    catchup = False,
    tags = ["flipkart", "master"],
    default_args = default_args,
)

def master_orchestrator():

    trigger__upsert = TriggerDagRunOperator(
        task_id="trigger_upsert_etl",
        trigger_dag_id="flipkart_upsert_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )

    trigger_etl = TriggerDagRunOperator(
        task_id="trigger_etl",
        trigger_dag_id="flipkart_fact_table_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )
    
    trigger_attendence = TriggerDagRunOperator(
        task_id="trigger_attendance",
        trigger_dag_id="flipkart_fact_attendance_etl",
        wait_for_completion=True,
        poke_interval=30,
        failed_states=["failed"],
    )

    # ==================== STARTING TASKS ====================
    trigger__upsert >> trigger_etl >> trigger_attendence

master_orchestrator()
