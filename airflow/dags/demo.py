import requests
import psycopg2

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

from datetime import datetime, date
from dotenv import dotenv_values
config = dotenv_values(".env")


def get_data_emas():
    url = "https://harga-emas-antam.p.rapidapi.com/"
    headers = {
        "X-RapidAPI-Key": config['RAPID_API_KEY'],
        "X-RapidAPI-Host": "harga-emas-antam.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers)
    datas = response.json()
    output = ''
    for data in datas['rows']:
        if data['gram'] == '1':
            output = ([datetime.strptime(data['tanggal'], '%Y-%m-%d %H:%M:%S').date(), data['jual'], data['beli']])

    try:
        connection = psycopg2.connect(user=config['PG_USER'],
                        password=config['PG_PASSWORD'],
                        host="postgres",
                        port="5432",
                        database="postgres")
        
        cursor = connection.cursor()
        postgres_insert_query = """ INSERT INTO public.emas_price (date, buy, sell) VALUES (%s,%s,%s)"""
        record_to_insert = (output[0], output[2], output[1])
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        cursor.close()
        connection.close()
    
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into emas_price table", error)


def get_data_btc():
    url = 'https://indodax.com/api/ticker/btcidr'
    response = requests.get(url)
    data = response.json()['ticker']
    output = [date.today(), data['last'], data['buy'], data['sell'], data['high'], data['low']]

    try:
        connection = psycopg2.connect(user=config['PG_USER'],
                        password=config['PG_PASSWORD'],
                        host="postgres",
                        port="5432",
                        database="postgres")
        
        cursor = connection.cursor()
        postgres_insert_query = """ INSERT INTO public.btc_price (date, last, buy, sell, high, low) VALUES (%s,%s,%s,%s,%s,%s)"""
        record_to_insert = (output[0], output[1], output[2], output[3], output[4], output[5])
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        cursor.close()
        connection.close()
    
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into btc_price table", error)


def get_data_ihsg():
    url = "https://yahoo-finance127.p.rapidapi.com/historic/%5EJKSE/1d/1d"
    headers = {
        "X-RapidAPI-Key": config['RAPID_API_KEY'],
        "X-RapidAPI-Host": "yahoo-finance127.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers)
    date = datetime.fromtimestamp(response.json()['timestamp'][0]).strftime('%Y-%m-%d')
    ihsg_data = response.json()['indicators']['quote'][0]
    output = [date, ihsg_data['volume'][0], ihsg_data['low'][0], ihsg_data['high'][0], ihsg_data['close'][0]]

    try:
        connection = psycopg2.connect(user=config['PG_USER'],
                        password=config['PG_PASSWORD'],
                        host="postgres",
                        port="5432",
                        database="postgres")
        
        cursor = connection.cursor()
        postgres_insert_query = """ INSERT INTO public.ihsg_price (date, volume, low, high, close) VALUES (%s,%s,%s,%s,%s)"""
        record_to_insert = (output[0], output[1], output[2], output[3], output[4])
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        cursor.close()
        connection.close()
    
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into ihsg_price table", error)



with DAG(
     dag_id="Korelasi-Harga-Emas-Bitcoin-IHSG-Workflow",
     start_date=datetime(2023, 8, 16),
     schedule="0 17 * * *",
    ) as dag:

    start = BashOperator(task_id="start", bash_command="start")

    get_data_emas_task = PythonOperator(
        task_id='Get-Gold-Price',
        python_callable=get_data_emas,
    )

    get_data_btc_task = PythonOperator(
        task_id='Get-BTC-Price',
        python_callable=get_data_btc,
    )

    get_data_ihsg_task = PythonOperator(
        task_id='Get-IHSG-Price',
        python_callable=get_data_ihsg,
    )

    start >> get_data_emas_task
    start >> get_data_btc_task
    start >> get_data_ihsg_task

