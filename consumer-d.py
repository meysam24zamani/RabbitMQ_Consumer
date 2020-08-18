import pika
import json
import config as cfg
import argparse
import logging
from datetime import datetime as dt
import os
import re
from time import gmtime, strftime
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
 
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

channel.queue_declare(queue=d["QUEUE_TOPIC_DELETE"], durable=True)
channel.exchange_declare("exchangeA", durable=True)
channel.queue_bind(d["QUEUE_TOPIC_DELETE"], "exchangeA", routing_key=None, arguments=None)

def callback(ch, method, properties, body):
    body = json.loads(body)
    body = body if isinstance(body, list) else [body]
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
        try:
            es_client.delete(index=index['_index'],doc_type="_doc",id=index['_id'])
        except NotFoundError as err:
            msg = f"The delete operation failed with the following message: {err}"
            logging.warning(msg)
            print(msg)
        else:
            msg2 = "Successfully deleted record in ELK..."
            logging.info(msg2)
            print(msg2)

channel.basic_consume(queue=d["QUEUE_TOPIC_DELETE"],
                      auto_ack=True,
                      on_message_callback=callback)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()

#As I have been a team member of pars ertebat (marketing department) since 5 years ago, 
# one of my main concerns as a marketing person, was data management system and avoid missing and forgetting or even deleting data that 
# company spends lots of money and energy in order to collect them.

# After switching to data science field as my master studying in UPC university of Barcelona and now after finishing my 4th semester, 
# I almost going to finish my study in August 2020. I have been studding and working in Data science field since 2 years ago and now i can say
# I have quiet useful and good experience and knowledge in this field. 
# 
# Now as a team member of parsertebat, I like to share my knowledge and use them in order to manage, organize and centralize all kind of data in 
# parsertebat Which I think realy needs it and could be useful in decision making step for managers and help them to have useful refrence of data
# which has meaning for them and make sence to looking at them before their final decisions in any related issues. 
# 
# for that, I am suggesting to have a Data managment Department in our company and i am interesting to continue my work in parsErtebat as a data 
# engineering person. 
# 
# I think it would be better to start with marketing data which comes mostly from Seminars, Exhibitions, events of parsErtebat.
# Later on we can focus on website data, after sales data and once we start trusting this mecanism and data warehousing system, 
# we can start working on sales and even system logs data from inside company in order to can track any down time of any internal system in company. 
# 
# What ever data with any kind of format and structure has this possiblity to add to this system and store in unique data warehousing 
# and from that point we will be able to query on our data and retrivew any kind of usful information with details.
# 
# So basicaly this system will start working with 3 main steps:
# 1- Extraction data 
# 2- Transforamtion data
# 3- load data  
#
# and once we have all kind of data loaded in data warehousing system, We can start to visualize them with most famos tools that these
# days use for visualizing data. exploration and decision based on our data history that we stored them all in our data warehousing 
# without missing even one value, one letter or one number that may use for decision making strategy or discoverig on our data. 
#  