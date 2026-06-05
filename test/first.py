from airflow import DAG
from datetime import datetime
from airflow.decorators import task

with DAG(
    dag_id = "JASKIRAT-my-first-dag",
    start_date = datetime(2026,1,1),
    schedule = None,
    catchup = False
) as dag :

  @task
  def start():
    print("helloooooo")

  @task
  def middle1():
    print("middle_1")
    
  @task
  def middle2():
    print("middle_2")

  @task
  def end():
    print("byeeeeee")

  t1 = start()
  t2 = middle1()
  t3 = middle2()
  t4 = end()

  t4 >> [t2,t3] >> t1
