# MIT No Attribution

# Copyright 2021 AWS

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import boto3
import os
from datetime import datetime
import logging
import boto3
import os
from botocore.exceptions import ClientError
import json
import markdown

AWS_REGION = os.getenv("AWS_REGION")
SQS_URI = os.getenv("COPILOT_QUEUE_URI")
ENV_NAME = os.getenv("COPILOT_ENVIRONMENT_NAME")
LOGGING_LEVEL = logging.INFO if ENV_NAME == "production" else logging.INFO
DEBUG_MODE = False if ENV_NAME == "production" else True
logging.basicConfig(level=LOGGING_LEVEL)

sqs_client = boto3.client("sqs", region_name=AWS_REGION)

dynamodb = boto3.resource('dynamodb')


def save_data(request_ID, markdown, html):
    try:
        table = dynamodb.Table(os.getenv("MARKDOWNTABLE_NAME"))
        table.update_item(
            Key={'ID': request_ID},
            UpdateExpression="set message_html=:html, request_date=:sts",
            ExpressionAttributeValues={
                ':markdown': markdown,
                ':html': html,
                ':sts': datetime.now().strftime("%m-%d-%Y %H:%M:%S")
            })
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
    except ClientError:
        logging.error('Could not delete the meessage from the - {}.'.format(
            SQS_URI), exc_info=True)
        raise
    else:
        return response


if __name__ == '__main__':
    while True:
        messages = receive_queue_message()
        if "Messages" in messages:
            for msg in messages['Messages']:
                try:
                    receipt_handle = msg['ReceiptHandle']
                    message = json.loads(msg['Body'])
                    payload = json.loads(message["Message"])["payload"]
                    data = {}
                    data['request_ID'] = payload['request_ID']
                    data['text'] = payload['text']

                    html = markdown.markdown(data["text"])
                    save_data(data['request_ID'], data["text"], html)
                    logging.info("Request received with ID {}. Input text {} and converted into Markdown: {}".format(
                        data["request_ID"], data["text"], html))
                except:
                    logging.error(
                        "Problem on processing request {}. Latest data {}".format(data["request_ID"], data), exc_info=True)
                finally:
                    logging.info('Deleting message from the queue...')
                    resp_delete = delete_queue_message(receipt_handle)
                logging.info(
                    'Received and deleted message(s) from {} with message {}.'.format(SQS_URI, resp_delete))
