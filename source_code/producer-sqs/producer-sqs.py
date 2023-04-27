import os
import json
import boto3
import sys
import traceback
import uuid
import os
from datetime import datetime
from flask import Flask
from flask import request as _request
from flask import jsonify
import logging
import time

#Uncoment in FASE9
# from aws_xray_sdk.core import xray_recorder, patch_all
# from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

# patch_all()

app = Flask(__name__)

#Uncoment in FASE9
# xray_recorder.configure(service='TODOAPP-Producer')
# XRayMiddleware(app, xray_recorder)

SNS_ARN = json.loads(os.getenv('COPILOT_SNS_TOPIC_ARNS'))
AWS_REGION = os.getenv("AWS_REGION")
sns_client = boto3.client('sns', region_name=AWS_REGION)

ENV_NAME = os.getenv("COPILOT_ENVIRONMENT_NAME")
LOGGING_LEVEL = logging.INFO if ENV_NAME == "PROD" else logging.DEBUG
DEBUG_MODE = False if ENV_NAME == "PROD" else True
logging.basicConfig(level=LOGGING_LEVEL)



@app.route('/health', methods=['GET'])
def healthcheck():
    data = {"status": "ok"}
    return jsonify(data), 200


@app.route('/api/pub', methods=['POST'])
def process():
    req = _request.get_json()
    logging.info(req)
    try:
        if "text" not in req:
            return jsonify({"error": "Parameters missing"}), 422

        if not req["text"]:
            return jsonify({"error": "Parameters missing"}), 422

        request_id = str(uuid.uuid4())
        resp_sns = sns_client.publish(
            TopicArn=SNS_ARN["todoapp-topic"],
            Message=json.dumps(
                {"payload": {"request_ID": request_id, "text": req["text"]}}))
        logging.info(resp_sns)
        return jsonify({"request_ID": request_id}), 200

    except:
        logging.error("Error on processing request", exc_info=True)
        return jsonify({"error": "error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)