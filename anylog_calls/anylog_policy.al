#----------------------------------------------------------------------------------------------------------------------#
# :steps:
#   1. check if policy exists
#   2. create policy
#   3. declare policy
#   4. `run msg client` to accept policies via REST POST
# :sample policy:
# {'mapping' : {'id' : 'ai-mnist-fl',
#              'dbms' : 'bring [dbms]',
#              'table' : 'bring [table]',
#              'timestamp' : 'bring [timestamp]',
#              'readings' : 'data',
#              'schema' : {'file' : {'root' : False,
#                                    'blob' : True,
#                                    'bring' : '[image]',
#                                    'apply' : 'base64decoding',
#                                    'type' : 'varchar'},
#                          'round_number' : {'root' : False,
#                                            'type' : 'int',
#                                            'bring' : '[round_number]'},
#                          'data_type' : {'root' : False,
#                                         'type' : 'string',
#                                         'bring' : '[data_type]'},
#                          'label' : {'root' : False,
#                                     'type' : 'int',
#                                     'bring' : '[data_type]'}}}}
# :sample data:
# {
#    'dbms': 'mnist_fl',
#    'table': 'train_node1',
#    'timestamp': '2025-01-13T19:03:17.780102',
#    'data': {
#        'round_number': 1,
#        'data_type': 'train',
#        'image': '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYFBgYGBwkIBgcJBwYGCAsICQoK
#                 CgoKBggLDAsKDAkKCgr/wAALCAAcABwBAREA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFB
#                 AQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1h
#                 ZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5
#                 ufo6erx8vP09fb3+Pn6/9oACAEBAAA/APwCtra4vLiO0tIHlllcJFFGpZnYnAAA5JJ7V9mfB7/g3m/4LMfHC0a+8I/sGeLNPiEbOG8
#                 XXFnoRYAgcLqM0DE/MCOORkjIBrd+K3/Bv3+1P+z7eeLtP/aL/aV/Z+8BXPg3w5Fq2o2fiT4oAXNy0iyutlBbwQSzSXJjjWTaUCb',
#        'label': 5
#    }
# }
#----------------------------------------------------------------------------------------------------------------------#


on error ignore
set create_policy = false

:set-params:
policy_id = ai-mnist-fl
policy_id = blockchain get mapping where id = !policy_id
if !policy_id goto run-mqtt
if not !policy_id and !create_policy == true then goto policy-error

<new_policy={
    "mapping": {
        "id": !policy_id,
        "dbms": "bring [dbms]",
        "table": "bring [table]",
        "schema": {
            "timestamp": {
                "type": "timestamp",
                "default": "now()",
                "bring": "[timestamp]"
            },
            "round_number": {
                "type": "int",
                "default": -1,
                "bring": "[round_number]"
            },
            "data_type": {
                "type": "string",
                "default": "train",
                "bring": "[data_type]"
            },
            "label": {
                "type": "int",
                "default": 1,
                "bring": "[label]"
            },
            "file": {
                "blob": true,
                "bring": "[image]",
                "extension": "png",
                "apply": "opencv",
                "hash": "md5",
                "type": "varchar"
            }
        }
    }
}>


:publish-policy:
process !local_scripts/policies/publish_policy.al
if !error_code == 1 then goto sign-policy-error
if !error_code == 2 then goto prepare-policy-error
if !error_code == 3 then goto declare-policy-error

set create_policy = true
goto set-params

:run-mqtt:
on error goto msg-error
<run msg client where broker=rest and port=!anylog_rest_port and user-agent=anylog and log=false and topic=(
    name=!policy_id and
    policy=!policy_id
)>

:end-script:
end script

:terminate-scripts:
exit scripts

:test-policy-error:
echo "Invalid JSON format, cannot declare policy"
goto end-script

:sign-policy-error:
print "Failed to sign cluster policy"
goto terminate-scripts

:prepare-policy-error:
print "Failed to prepare mapping policy for publishing on blockchain"
goto terminate-scripts

:declare-policy-error:
print "Failed to declare mapping policy on blockchain"
goto terminate-scripts

:policy-error:
print "Failed to publish mapping policy for an unknown reason"
goto terminate-scripts


:msg-error:
echo "Failed to deploy MQTT process"
goto end-script






