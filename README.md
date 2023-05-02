
# aws-copilot-demo
## Demo do funcionamento do AWS Copilot

### Requisitos:
- AWS CLI V2 ( https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) 
- Copilot CLI (https://aws.github.io/copilot-cli/docs/getting-started/install/)
- Docker
- AWS Permissions (Temp creds ou Instance Role)

### Step 1 - Clone the repo

````
git clone https://github.com/alexandreags/aws-copilot-demo.git
````

### 2 -Initialize APP
  - Goto Root folder cloned from repository:
````
cd aws-copilot-demo
````
- Use copilot to nitialize the main app 
```
copilot init --app todoapp-main --dockerfile source_code/main/Dockerfile --name todoapp-main --type  "Load Balanced Web Service"
```
  - When Copilot asks to deploy into a test environment, choose N.
  - From there, copilot created:
    - Cloudformation for stack infrastructure-roles
    - A StackSet admin role assumed by CloudFormation to manage regional stacks
    - An IAM role assumed by the admin role to create ECR repositories, KMS keys, and S3 buckets
    - The directory copilot will hold service manifests for application created.
    - The manifest for service todoapp at **copilot/todoapp-main/manifest.yml**
    - Update regional resources with stack set **"todoapp-main"**
    - Folder Structure:
```
├── copilot
	│   └── todoapp-main
	│      └── manifest.yml
	├── LICENSE
	├── README.md
	└── source_code
```    
### 3 - Configure APP Paths
   - In copilot/todoapp-main/manifest.yaml edit the http directive:

    http:
      # Requests to this path will be forwarded to your service.
      path: '/' #the main path of the Application
      # You can specify a custom health check path. The default is "/".
      healthcheck:
        path: '/health_check' # Path for healtch in ALB
        success_codes: '200,301'

### 4 - Initialize Staging Environment: 
Environments contains all the AWS resources to provision a secure network (VPC, subnets, security groups, and more), as well as other resources that are meant to be shared between multiple services like an Application Load Balancer or an ECS Cluster. For example, when you deploy your service into a _test_ environment, your service will use the _test_ environment's network and resources. Your application can have multiple environments, and each will have its own networking and shared resources infrastructure.
In thist demo we will use 2 environments: staging and production.
```
copilot env init --name staging --default-config --profile default 
```
```
copilot env init --name production --default-config --profile default 
```
- Copilot will create a manifest with default settings in **copilot/environments/staging/manifest.yml** and **copilot/environments/production/manifest.yml**
- You can import existing VPCs or ALB in manifest configuration. In this case will use the default setting (Copilot will create everything for us.)
- Note that copilot just created manifests files and basic roles permissions, but not created the resources yet.
### 5 - Deploy Staging Environment
```    
copilot env deploy --name staging
```
- Copilot will create VPC, Subnets and Cluster for deployment. Note that default configuration create the vpc and the resources from scratch.   

### 6 - Create Database for app:
- If you look at **source_code/main/todoapp/settings.py**, the code contains a section to connect to a Database:

        DBINFO = json.loads(os.environ.get('TODOAPPDB_SECRET', '{}'))
        DATABASES = {
           'default': {
               'ENGINE': 'django.db.backends.postgresql',
               'HOST': DBINFO['host'],
               'PORT': DBINFO['port'],
               'NAME': DBINFO['dbname'],
               'USER': DBINFO['username'],
               'PASSWORD': DBINFO['password'],
           }
        }
- But this Database doesnt exists in project yet. Lets Create one:
```
copilot storage init -n todoapp-db -t Aurora -w todoapp-main --engine PostgreSQL
```
- When the Copilot asks for deletetion behavior, choose yes. We are choosing the DB lifecycle to follow the application lifecycle. If we delete the application, the DB will be deleted also.
- When asks for thr name of the initial database in your cluster? Choose **todoappdb**
- Copilot will update environment variables in the service and we can get the valuess of the database using the Environment variable **TODOAPPDB_SECRET**

### 7 Deploy Everything!
  
- Now we can deploy all resources (Services, Databases, Docker Images, ECR Repository, ECS, Etc.)
```
copilot deploy --name todoapp-main
```

- The process take about 10 min to complete.
- After the process complete, copilot will show you the url of the Loadbalancer Service:
- You can access your service at **http://<ALB Address>/todos/list** over the internet. (The main root URL dont access the service, this was set up on purpose)
 
### 8 Adding More Services to our Application

- Until now, we have deployed a single application whit a Database. AWS ECS works with services, which are basically Docker containers running Workloads.
- Thinking about the microservices model, we can implement several services to work together.
- Now we are going to add a pub/sub service to our application. So, everytime a task is posted, we will put a POST request to a **Producer** Service. That Service will notify the task data to a SNS Service.
- A **Consumer** Service will read a SQS Queue and for eacho record will put the data into a DynamoDB Table. With this we can simulate an Application with several services working simultaneously
- Lets Add 2 services to you Application: A Producer BackEnd service, that will put events in SNS. And a Worker Service to act as a Consumer that will query a SQS Queue
```    
copilot svc init --name producer-sqs --svc-type "Backend Service" 
--dockerfile source_code/producer-sqs/Dockerfile
```
```
copilot svc init --name consumer-sqs --svc-type "Worker Service" --dockerfile source_code/consumer-sqs/Dockerfile
```
- This will create just the manifest files and permissions. We not have deployed yet.    
- Now, we will create a DynamoDB Table to consumer store results:
```
copilot storage init -t DynamoDB -n todoapp-table --partition-key ID:S --no-lsi --no-sort -w consumer-sqs
```
- Edit the manifest: copilot/producer-sqs/manifest.yml:
```
    # Distribute traffic to your service.
        http:
          # Requests to this path will be forwarded to your service.
          # To match all requests you can use the "/" path.
          path: 'api/pub'
          # You can specify a custom health check path. The default is "/".
          healthcheck: '/health'
        publish:
          topics:
            - name: todoapp-topic
```
- This will instruct copilot to respond in the path /api/pub and create a SNS topic associated with a SQS Queue
- On the same file, in network, add the private directive to turn ALB in private access only:
```
    network:
      connect: true # Enable Service Connect for intra-environment traffic between services.
      vpc:
        placement: private
```
- Edit the file copilot/consumer-sqs/manifest.yml:
```
    subscribe:
      topics:
        - name: todoapp-topic
          service: producer-sqs
      queue:
        dead_letter:
          tries: 5
```
- In the code above, We are instructing the consumer service do access the Queue from the producer service. Copilot will automatically handle this for us.
- Deploy the new services:
```
    - copilot svc deploy --name producer-sqs --env staging
    - copilot svc deploy --name consumer-sqs --env staging
```
- With the services deployed, uncomment the section in the main app that calls the producer http service and redeploy the main service (/aws-copilot-demo/source_code/main/todos/views.py)
```
    #To reach the "api" service behind the internal load balancer
    # Uncoment in FASE8
    endpoint = f"http://producer-us-east-1-sqs.%s.%s.internal/api/pub" % (os.environ.get("COPILOT_ENVIRONMENT_NAME"), os.environ.get("COPILOT_APPLICATION_NAME"))
    data = {
    "id": str(uuid.uuid4()),
    "text": str(request.POST['content'])
    }
    response = requests.post(endpoint, json=data)
    
    print('Todo Content json data %s' % data )
    
    print("Status Code", response.status_code)
    print("JSON Response ", response.json())
```
- Now, when the user post a task, the main app will put data in the Aurora Database and POST data to the Producer Service.
```
copilot svc deploy --name todoapp-main --env staging
```
- After the process complete, post a task in the main app and check DynamoDB for the data.

### 9 Monitoring with Xray and Container Insights

- Now we enable application monitoring in all of your services to monitor the application and gather metrics.
    - In copilot/environments/staging/manifest.yml, change the observability setting to enble container insights:
```
        observability:
          container_insights: true
```
- Edit the 3 manifest files from each service in copilot folder: (copilot/<appname>/manifest.yml)
```
      sidecars:
        xray:
          port: 2000
          image: public.ecr.aws/xray/aws-xray-daemon:latest
```
- This enable xray sidecar within container.
- You need to add aditional permissions to service to publish metrics to xray. For each copilot/<appname>, create a folder named addons (if not exist).
- Create a file named iam.yml with the folloing configuration:
```
      Resources:
        XrayWritePolicy:
          Type: AWS::IAM::ManagedPolicy
          Properties:
            PolicyDocument:
              Version: '2012-10-17'
              Statement:
                - Sid: CopyOfAWSXRayDaemonWriteAccess
                  Effect: Allow
                  Action:
                    - xray:PutTraceSegments
                    - xray:PutTelemetryRecords
                    - xray:GetSamplingRules
                    - xray:GetSamplingTargets
                    - xray:GetSamplingStatisticSummaries
                  Resource: "*"
      
      Outputs:
        XrayAccessPolicyArn:
          Description: "The ARN of the ManagedPolicy to attach to the task role."
          Value: !Ref XrayWritePolicy
```
- Uncoment the sections that calls the xray daemon
/aws-copilot-demo/source_code/main/todos/views.py
```
#Uncoment in FASE 9
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
patch_all()
```
/aws-copilot-demo/source_code/main/todoapp/settings.py
```
Line 43: 'aws_xray_sdk.ext.django', #Uncoment In FASE9
Line 49: 'aws_xray_sdk.ext.django.middleware.XRayMiddleware', #Uncoment In FASE9
Line 59: XRAY_RECORDER = { #Uncoment In FASE9
    'AWS_XRAY_TRACING_NAME': 'TODOAPP-Main', # the segment name for segments generated from incoming requests
    'AWS_XRAY_DAEMON_ADDRESS': 'localhost:2000'	
}
```
/aws-copilot-demo/source_code/consumer-sqs/consumer-sqs.py
```
#Change in Fase9
# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch_all

# patch_all()

#xray_recorder.configure(service='TODOAPP-Consumer')

Line 81: xray_recorder.begin_segment("TODOAPP-Consumer") #Uncoment In FASE9
Line 105:         xray_recorder.end_segment() #Uncoment In FASE9
```
/aws-copilot-demo/source_code/producer-sqs/producer-sqs.py
```
#Uncoment in FASE9
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

patch_all()

app = Flask(__name__)

#Uncoment in FASE9
xray_recorder.configure(service='TODOAPP-Producer')
XRayMiddleware(app, xray_recorder)
```
- Redeploy All Services:
- copilot svc deploy --name todoapp-$REGION-main --env staging && copilot svc deploy --name producer-$REGION-sqs --env staging && copilot svc deploy --name consumer-$REGION-sqs --env staging          
- Generate some random post data
- Check X-RAY Service MAP in CloudWatch
