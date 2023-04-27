import boto3
import os
from datetime import datetime
import logging
import boto3
import os
from botocore.exceptions import ClientError
import json, time

#Change in Fase9
# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch_all

# patch_all()

#xray_recorder.configure(service='TODOAPP-Consumer')


#########



AWS_REGION = os.getenv("AWS_REGION")
SQS_URI = os.getenv("COPILOT_QUEUE_URI")
ENV_NAME = os.getenv("COPILOT_ENVIRONMENT_NAME")
LOGGING_LEVEL = logging.INFO if ENV_NAME == "production" else logging.INFO
DEBUG_MODE = False if ENV_NAME == "production" else True
logging.basicConfig(level=LOGGING_LEVEL)

sqs_client = boto3.client("sqs", region_name=AWS_REGION)

dynamodb = boto3.resource('dynamodb')


def save_data(request_ID, message):
    try:
        table = dynamodb.Table(os.getenv("TODOAPPTABLE_NAME"))
        table.update_item(
            Key={'ID': request_ID},
            UpdateExpression="set tarefa=:tarefa, request_date=:sts",
            ExpressionAttributeValues={
                ':tarefa': message,
                ':sts': datetime.now().strftime("%m-%d-%Y %H:%M:%S")
            })
        logging.info("Mensagem Gravada no Dynamodb!")
        return True
    except Exception:
        logging.error("Error on saving data into DynamoDB", exc_info=True)
        return False


def receive_queue_message():
    try:
        response = sqs_client.receive_message(
            QueueUrl=SQS_URI, WaitTimeSeconds=5, MaxNumberOfMessages=1)
    except ClientError:
        logging.error('Could not receive the message from the - {}.'.format(
            SQS_URI), exc_info=True)
        raise
    else:
        return response


def delete_queue_message(receipt_handle):
    try:
        response = sqs_client.delete_message(QueueUrl=SQS_URI,
                                             ReceiptHandle=receipt_handle)
        logging.info("Mensagem Deletada: \n %s " % response)
    except ClientError:
        logging.error('Could not delete the meessage from the - {}.'.format(
            SQS_URI), exc_info=True)
        raise
    else:
        return response



if __name__ == '__main__':
    while True:
        
        #xray_recorder.begin_segment("TODOAPP-Consumer") #Uncoment In FASE9
        messages = receive_queue_message()
        if "Messages" in messages:
            logging.info("Mensagem Recebida: \n %s " %  messages['Messages'])
            for msg in messages['Messages']:
                try:
                    receipt_handle = msg['ReceiptHandle']
                    message = json.loads(msg['Body'])
                    payload = json.loads(message["Message"])["payload"]
                    data = {}
                    data['request_ID'] = payload['request_ID']
                    data['text'] = payload['text']
                    save_data(data['request_ID'], data["text"])
                    logging.info("Request received with ID {}. Input text {} ".format(
                        data["request_ID"], data["text"]))
                except:
                    logging.error(
                        "Problem on processing request {}. Latest data {}".format(data["request_ID"], data), exc_info=True)
                finally:
                    logging.info('Deleting message from the queue...')
                    resp_delete = delete_queue_message(receipt_handle)
                logging.info(
                    'Received and deleted message(s) from {} with message {}.'.format(SQS_URI, resp_delete))
        time.sleep(3)
        #xray_recorder.end_segment() #Uncoment In FASE9