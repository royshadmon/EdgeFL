import ast
import requests


# Basic AnyLog / EdgeLake commands - we could replace this with AnyLog-API\
def __get_cmd(node_conn:str, command:str, destination:str=None):
    """
    Execute GET commands against EdgeLake
        - get data nodes
        - blockchain get
        - sql query (requires destination)
        - etc.
    :args:
        node_conn:str - query node connection information
        command:str - query to execute (sql [db_name] ... )
        destination:str - specific TCP connection info to send request to. If not provied, send request to network
    :params:
        headers:dict - REST header information
       response:requests.get - REST request response
    :return:
        query result
    """
    headers = {
        'command': command,
        'User-Agent': 'AnyLog/1.23'
    }

    if destination:
        headers['destination'] = destination

    try:
        # Send the GET request
        response = requests.get(url=node_conn, headers=headers)

        # Raise an HTTPError if the response code indicates failure
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise IOError(f"Failed to execute SQL query: {e}")
    except json.JSONDecodeError:
        raise ValueError("The response from the request is not valid JSON.")

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        try:
            return ast.literal_eval(response.text)
        except ValueError:
            return response.text


def get_dbms_tables(query_node=str):
    """
    From blockchain metdata (table policies) get logical daatabase and table name(s)
    :args:
        query_node:str - REST connection information to the Query node
    :params:
        db_tables:str - comma seperated list of tables + databases (db_name.table_name)
    :return:
        db_tables
    :code-replace:
        node_server.py - lines 91-96
    """
    blockchain_get = "blockchain get table bring [*][dbms] . [*][name] separator=,"
    db_tables = __get_cmd(node_conn=query_node, command=blockchain_get, destination=None)
    return db_tables


def get_columns(query_node:str, db_name:str, table:str):
    """
    get list of columns for a given table
    :args:
        query_node:str - REST connection information to the Query node
        db_name:str - logical database name
        table:str - logical table name
    :params:
        command:str - command to execute
        columns:list - list of columns in table
    :return:
        columns
    """
    command = f"get columns where dbms={db_name} and table={table} and format=json"
    output = __get_cmd(node_conn=query_node, command=command, destination=None)
    # remove EdgeLake defined columns
    columns = [x for x in output.keys() if x not in ['row_id', 'insert_timestamp', 'tsd_name', 'tsd_id']]
    return columns

def check_tables_and_databases(query_node:str):
    """
    Using blockchain metadata, check whether tables actually contain data
    :args:
        query_node:str - REST connection information to the Query node
    :params:
        db_tables:str - comma seperated list of tables + databases (db_name.table_name)
        query:str - SQL query
    :return:
        if Success returns True, when data DNE  raises ValueError
    :code-replace:
        node_server.py - lines 99-102
    """
    db_tables = get_dbms_tables(query_node=query_node)
    query = f"sql %s format=json and stat=false select count(*) as count from %s"

    for db_table in db_tables.split(','):
        db_name, table_name = db_table.split('.')
        output = __get_cmd(node_conn=query_node, command=query % (db_name, table_name), destination='network')
        try:
            result = output['Query'][0]
            if 'count' not in result or int(result['count']) <= 0:
                raise ValueError(f"No data found in {db_table}.")
        except Exception:
            raise ValueError(f"No data found in {db_table}.")

    return True


def sample_queries(query_node:str, db_name:str, table_name:str, destination:str='network'):
    """
    Query data basing on the columns in table
    :args:
        query_node:str - REST connection information to the Query node
        db_name:str - logical database name
        table:str - logical table name
        destination:str - specific TCP connection info to send request to. If not provied, send request to network
    :params:
        columns:;list - list of columns in a given database.table
         query:str - query to execute
         output:str - raw result from query
         result:list - extracted result from query

    :print:
        result
    :code-replace:
        get_all_test_data function
    """
    columns = get_columns(query_node=query_node, db_name=db_name, table=table_name)
    query = f"sql {db_name} format=json and stat=false select {','.join(columns)} FROM {table_name} LIMIT 10"
    output = __get_cmd(node_conn=query_node, command=query, destination=destination)
    try:
        result = output['Query']
    except Exception:
        raise ValueError(f"No data found in {db_table}.")

    print(result)

# check_tables_and_databases(query_node='http://10.0.0.147:32049')
sample_queries(query_node='http://10.0.0.147:32049', db_name='mnist_fl', table_name='room_12004_train', destination='network')