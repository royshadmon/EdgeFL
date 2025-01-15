#----------------------------------------------------------------------------------------------------------------------#
# Connect to database(s) and accept blob data
#----------------------------------------------------------------------------------------------------------------------#
on error ignore

:set-params:
default_dbms = mnist_fl
db_type = psql
db_user = admin
db_passwd = demo
db_ip = 10.0.0.131
db_port = 5432

partition_column = insert_timestamp
partition_interval = day

nosql_type = mongo
nosql_ip = 10.0.0.131
nosql_port = 27017
nosql_user = admin
nosql_passwd = passwd

:postgres-conn:
on error goto psql-conn-error
<connect dbms !default_dbms where
    type=!db_type and
    user = !db_user and
    password = !db_passwd and
    ip = !db_ip and
    port = !db_port
>

:set-partition:
on error call set-partition-error
partition !default_dbms * using !partition_column by day
<schedule time=1 day and name="Drop AI Partitions"
    task drop partition where dbms=!default_dbms and table =* and keep=3>

:mongo-conn:
on error goto mongo-conn-error

if !nosql_user and !nosql_passwd then
<do connect dbms !default_dbms where
    type=!nosql_type and
    ip=!nosql_ip and
    port=!nosql_port and
    user=!nosql_user and
    password=!nosql_passwd
>
else connect dbms !default_dbms where type=!nosql_type and ip=!nosql_ip and port=!nosql_port

on error call blobs-archiver-error
<run blobs archiver where
    dbms=true and
    folder=false and
    compress=true and
    reuse_blobs=true
>

:end-script:
end script

:terminate-scripts:
exit scripts

:operator-db-error:
echo "Error: Unable to connect to almgm database with db type: " !db_type ". Cannot continue"
goto terminate-scripts

:set-partition-error:
echo "Error: Failed to set partitioning"
return


