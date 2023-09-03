import os
import psycopg2
from math import sqrt
from dotenv import load_dotenv

load_dotenv()


def get_correlation(start_date, end_date, input1, input2):
    connection = psycopg2.connect(user=os.getenv('PG_USER'),
                    password=os.getenv('PG_PASSWORD'),
                    host="127.0.0.1",
                    port="6543",
                    database="postgres")

    cursor = connection.cursor()
    cursor.execute(f""" 
        SELECT 
            btc.date, btc.last AS bitcoin, ihsg.close AS ihsg, emas.buy AS emas_buy, emas.sell AS emas_sell
        FROM 
            public.btc_price AS btc
        LEFT JOIN 
            public.emas_price AS emas on btc.date = emas.date
        LEFT JOIN 
            (SELECT DISTINCT ON (date) date, updated_value AS close
            FROM (SELECT row_number() over (order by Null) as id, t1.date,COALESCE(t1.close, t2.close) AS updated_value
                FROM (SELECT row_number() over (order by b1.date) as id, b1.date, t1.close
                        FROM public.ihsg_price t1
                        FULL JOIN public.btc_price b1
                        ON t1.date = b1.date) AS t1
                LEFT JOIN
                    (SELECT row_number() over (order by b1.date) as id, b1.date, t1.close
                        FROM public.ihsg_price t1
                        FULL JOIN public.btc_price b1
                        ON t1.date = b1.date) AS t2
                ON t1.date > t2.date AND t2.close IS NOT NULL
                ORDER BY t1.date, id) AS source
            ORDER BY date, id) AS ihsg
        ON
            btc.date = ihsg.date
        WHERE btc.date >= '{start_date}' AND btc.date <= '{end_date}'
        ORDER BY 
            btc.date""")

    # transform result
    columns = list(cursor.description)
    result = cursor.fetchall()

    # make dict
    datas = []
    for row in result:
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col.name] = row[i]
        datas.append(row_dict)

    cursor.close()
    connection.close()

    sumXY = 0
    sumX = 0
    sumY = 0
    sumXsquare = 0
    sumYsquare = 0

    for data in datas:
        sumXY += (float(data[input1]) * float(data[input2]))
        sumX += float(data[input1])
        sumY += float(data[input2])
        sumXsquare += float(data[input1]) ** 2
        sumYsquare += float(data[input2]) ** 2

    coefficient = ((len(datas) * sumXY) - (sumX * sumY)) / \
        (sqrt(((len(datas) * sumXsquare) - (sumX ** 2)) * ((len(datas) * sumYsquare) - (sumY ** 2))))
    
    status = ''
    if coefficient > 0 and coefficient <= 0.25:
        status =  "Very Weak Positive Correlation"
    elif coefficient >= 0.251 and coefficient <= 0.5:
        status = "Medium Positive Correlation"
    elif coefficient >= 0.501 and coefficient <= 0.75:
        status = "Strong Positive Correlation"
    elif coefficient >= 0.751 and coefficient <= 0.999:
        status = "Very Strong Positive Correlation"
    elif coefficient == 1:
        status = "Perfect Positive Correlation"

    elif coefficient < 0 and coefficient >= -0.25:
        status =  "Very Weak Negative Correlation"
    elif coefficient <= -0.251 and coefficient >= -0.5:
        status = "Medium Negative Correlation"
    elif coefficient <= -0.501 and coefficient >= -0.75:
        status = "Strong Negative Correlation"
    elif coefficient <= -0.751 and coefficient >= -0.999:
        status = "Very Strong Negative Correlation"
    elif coefficient == -1:
        status = "Perfect Negative Correlation"
    

    return {"coefficient": coefficient, "status": status}

