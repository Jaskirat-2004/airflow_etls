from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.decorators import dag
import pendulum


default_args = {
    "owner": "JASKIRAT",
    
}

@dag(
    dag_id = "lms_master_orchestrator",
    start_date = pendulum.datetime(2026,1,1),
    schedule = None,
    catchup = False,
    tags = ["lms", "master"],
    default_args = default_args,
)

def master_orchestrator():

    trigger_etl = TriggerDagRunOperator(
        task_id="trigger_etl",
        trigger_dag_id="lms_etl_dynamic",
        wait_for_completion=True
    )

    trigger_fact_tables = TriggerDagRunOperator(
        task_id="trigger_fact_tables",
        trigger_dag_id="lms_fact_table_etl",
        wait_for_completion=True
    )
    
    trigger_fact_user_x_lesson_merged = TriggerDagRunOperator(
        task_id="trigger_fact_user_x_lesson_merged",
        trigger_dag_id="lms_fact_user_x_lesson_merged",
        wait_for_completion=True
    )

    trigger_etl >> trigger_fact_tables >> trigger_fact_user_x_lesson_merged

master_orchestrator()

