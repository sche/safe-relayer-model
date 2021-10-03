import psycopg2
from dotenv import dotenv_values

config = dotenv_values(".env")

def main():
    conn = psycopg2.connect(host='external-db-access.gnosis.io', 
                            database='transaction_history',
                            user='safe_team_readonly',
                            password=config['PG_PASSWORD'],
                            sslmode='verify-ca', 
                            sslrootcert=config['SSL_CERT'])
    cur = conn.cursor()
    
    query = """
with t 
as 
(select safe_tx_hash, created, ethereum_tx_id
from history_multisigtransaction as t
where ethereum_tx_id is not null
order by created desc 
limit 100)

select t.safe_tx_hash, et.block_id, t.created, b.timestamp as executed, FLOOR(EXTRACT(EPOCH FROM (b.timestamp - t.created))) as created_to_executed_sec, et.tx_hash, et.gas_used, et.gas_price
from history_ethereumtx as et
join t on t.ethereum_tx_id = et.tx_hash
join history_ethereumblock as b on b.number = et.block_id
where EXTRACT(EPOCH FROM (b.timestamp - t.created)) > 0 --filter out transactions initiated not via our interface
    """
    
    # Use the COPY function on the SQL we created above.
    SQL_for_file_output = "COPY ({0}) TO STDOUT WITH CSV HEADER".format(query)
    
    # Set up a variable to store our file path and name.
    with open('transactions.csv', 'w') as f:
        cur.copy_expert(SQL_for_file_output, f)
    
    conn.close()

if __name__ == '__main__':
    main()
