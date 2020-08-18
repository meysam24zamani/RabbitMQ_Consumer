import pika
import json
import config as cfg
import argparse
import logging
from datetime import datetime as dt
import os
import re
from time import gmtime, strftime
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch.helpers import streaming_bulk

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] -- %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=f"/tmp/json_records_to_elk_task.log"
)

d = cfg.create_config_from_object(cfg.configs[os.getenv('ELK_ENV', 'local')])
pika_dict = {
    "host": d["RABBIT_HOST"],
    "port": d["RABBIT_PORT"],
    "virtual_host": d["RABBIT_VHOST"],
}

logging.info(f"Indexing and sending JSON file to ELK...")
es_client = Elasticsearch(d["ELK_URL"], http_auth=(d["ELK_USERNAME"], d["ELK_PASSWORD"]))
logging.info(f"ELK metadata: {es_client.info()}")

# breakpoint(Just for Pythons with version less than 3.7)
# import pdb; pdb.set_trace()
# breakpoint(Just for Python version 3.7 or upper)
# breakpoint()

credentials = pika.PlainCredentials(d["RABBIT_USER"], d["RABBIT_PASSWD"])
connection = pika.BlockingConnection(pika.ConnectionParameters(**pika_dict, credentials=credentials))
channel = connection.channel()

channel.queue_declare(queue=d["QUEUE_TOPIC_UPDATE"], durable=True)
channel.exchange_declare("exchangeA", durable=True)
channel.queue_bind(d["QUEUE_TOPIC_UPDATE"], "exchangeA", routing_key=None, arguments=None)

def callback(ch, method, properties, body):
    body = json.loads(body)
    body = body if isinstance(body, list) else [body]

    for i, element in enumerate(body[:], start=0):
        body[i]["project"] = {}
        body[i]["project"]["idproject"] = body[i]["projects"][0]["idproject"]
        body[i]["project"]["name"] = body[i]["projects"][0]["name"]

    for i, element in enumerate(body, start=0):
        for key in element.keys():
            if isinstance(element[key], dict):
                for key_2 in element[key].keys():
                    if isinstance(element[key][key_2], dict):
                        for key_3 in element[key][key_2].keys():
                            if key_3 == "enum":
                                pos = element[key][key_2]["value"]
                                element[key][key_2]["value"] = element[key][key_2]["enum"][pos]["en"]

    keys_to_remove1 = []
    for i, element in enumerate(body, start=0):
        # 1st level
        for key in element.keys():
            if (key == "role") or (key == "projects"):
                keys_to_remove1.append([i, key])
    for k in keys_to_remove1:
        del(body[k[0]][k[1]])

    keys_to_remove2 = []
    for i, element in enumerate(body, start=0):
        # 1st level
        for key in element.keys():
            if key == "template":
                for key_2 in element[key].keys():
                    if key_2 == "color":
                        keys_to_remove2.append([i, key, key_2])
    for k in keys_to_remove2:
        del(body[k[0]][k[1]][k[2]])

    keys_to_remove3 = []
    for i, element in enumerate(body, start=0):
        # 1st level
        for key in element.keys():
            # 2nd level
            if isinstance(element[key], dict):
                for key_2 in element[key].keys():
                    # 3rd level
                    if isinstance(element[key][key_2], dict):
                        for key_3 in element[key][key_2].keys():
                            if key_3 != "value":
                                keys_to_remove3.append([i, key, key_2, key_3])
    for k in keys_to_remove3:
        del(body[k[0]][k[1]][k[2]][k[3]])

    def yield_indexed_data():
        # for idx, record in enumerate(body):
        for record in body:
            # rx = re.compile('[^\w]')
            tpl_id = record.get('template', {}).get('idtemplate', None)
            tpl_time = record.get('updated', {}).get('date', None)
            record["updated"]["date"] = dt.strptime(tpl_time, "%Y-%m-%d %H:%M:%S.%f").astimezone().isoformat()
            index = {
                # "_index": rx.sub('_', f"records_{tpl_name}".lower()),
                "_index": f"records_{d['RABBIT_VHOST'].split('_')[-1]}_{tpl_id}",
                "_type": "_doc",
                # "_id": str(idx) + ',' + str(record["identity"])
                "_id": record["identity"]
            }
            yield {**index, **record}

    try:
        for ok, result in streaming_bulk(es_client, yield_indexed_data()):
            action, result = result.popitem()
            doc_id = f"{result.get('_id', 'NOT_FOUND')}"
            # Check if document has been successfully indexed
            if ok:
                logging.info(f"Success in '{action}' action. Result: {result}") 
            else:
                logging.error(f"Failed to {action} document {doc_id}: {result}")
                raise ElasticsearchException(f"Failed to {action} document {doc_id}: {result}")
 
        print(f'[{strftime("%Y-%m-%d %H:%M:%S", gmtime())}] Uploading JSON file of records to ELK...')
    
        print(f'[{strftime("%Y-%m-%d %H:%M:%S", gmtime())}] Done.')
    except Exception as e:
        print(e)


channel.basic_consume(queue=d["QUEUE_TOPIC_UPDATE"],
                      auto_ack=True,
                      on_message_callback=callback)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()