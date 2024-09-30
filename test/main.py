import json
import psycopg2
import pandas as pd
from psycopg2 import sql



def load_config(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


def connect_db(db_config):
    return psycopg2.connect(
        host=db_config['host'],
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password']
    )


def fetch_data(conn, schema, table):
    query = sql.SQL("SELECT * FROM {}.{}").format(
        sql.Identifier(schema),
        sql.Identifier(table)
    )
    return pd.read_sql(query, conn)


def sync_tables(source_conn, target_conn, schema, table):
    source_data = fetch_data(source_conn, schema, table)
    target_data = fetch_data(target_conn, schema, table)

    # Определение записей для вставки и обновления
    records_to_insert = source_data[~source_data.isin(target_data).all(axis=1)]

    report = {
        'total_source': len(source_data),
        'total_target': len(target_data),
        'planned_to_transfer': len(records_to_insert),
        'successful_transfers': 0,
        'failed_transfers': 0
    }

    insert_file_content = []

    for index, row in records_to_insert.iterrows():
        try:
            insert_query = sql.SQL("INSERT INTO {}.{} VALUES ({})").format(
                sql.Identifier(schema),
                sql.Identifier(table),
                sql.SQL(', ').join(sql.Placeholder() * len(row))
            )
            target_conn.cursor().execute(insert_query, tuple(row))
            insert_file_content.append((row.tolist(), 'Ок'))
            report['successful_transfers'] += 1
        except Exception as e:
            insert_file_content.append((row.tolist(), str(e)))
            report['failed_transfers'] += 1

    target_conn.commit()

    return report, insert_file_content


def main():
    config = load_config('config.json')

    source_conn = connect_db(config['source_db'])
    target_conn = connect_db(config['target_db'])

    overall_report = {
        'total_source': 0,
        'total_target': 0,
        'planned_to_transfer': 0,
        'successful_transfers': 0,
        'failed_transfers': 0
    }

    for table_info in config['tables']:
        schema = table_info['schema']
        table = table_info['table']

        report, insert_file_content = sync_tables(source_conn, target_conn, schema, table)

        overall_report['total_source'] += report['total_source']
        overall_report['total_target'] += report['total_target']
        overall_report['planned_to_transfer'] += report['planned_to_transfer']
        overall_report['successful_transfers'] += report['successful_transfers']
        overall_report['failed_transfers'] += report['failed_transfers']

        # Запись в файл для каждой таблицы
        with open(f'{table}_sync_report.txt', 'w') as f:
            for record in insert_file_content:
                f.write(f"INSERT INTO {schema}.{table} VALUES {record[0]} -- {record[1]}\n")

                # Запись общего отчета
            with open('overall_sync_report.txt', 'w') as f:
                f.write(json.dumps(overall_report, ensure_ascii=False, indent=4))

            source_conn.close()
            target_conn.close()

        if __name__ == "__main__":
            main()
