# aws-copilot-demo
Demo do funcionamento do AWS Copilot

Requisitos:
    - AWS CLI V2 ( https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) 
    - Copilot CLI
    - Docker (Ex: sudo yum install docker)
    - AWS Permissions (Temp creds ou Instance Role)

1 - Install Copilot CLI
    - https://aws.github.io/copilot-cli/docs/getting-started/install/

2 -Initialize APP
    - From the root folder od the repository:
    - set current region = REGION=$(aws ec2 describe-availability-zones --output text --query 'AvailabilityZones[0].[RegionName]')
    - copilot init --app todoapp-$REGION --dockerfile source_code/main/Dockerfile --name todoapp-$REGION-main --type  "Load Balanced Web Service"
    - When Copilot asks to deploy into a test environment, choose N.
    From there, copilot created:
    - Infrastructure for stack infrastructure-roles
    - A StackSet admin role assumed by CloudFormation to manage regional stacks
    - An IAM role assumed by the admin role to create ECR repositories, KMS keys, and S3 buckets
    - The directory copilot will hold service manifests for application todoapp-sa-east-1.
    - Wrote the manifest for service todoapp at copilot/<name>/manifest.yml
    - Update regional resources with stack set "<app-name>"
    FOLDER Structure:
    .
    ├── copilot
    │   └── <app-name>
    │       └── manifest.yml
    ├── LICENSE
    ├── README.md
    └── source_code
3 - Configure APP Paths
    - In copilot/<app-name>/manifest.yaml edit the http directive:
    http:
      # Requests to this path will be forwarded to your service.
      path: '/'
      # You can specify a custom health check path. The default is "/".
      healthcheck:
        path: '/health_check'
        success_codes: '200,301'
4 - Initialize Staging Environment
    - copilot env init --name staging --default-config --profile default
    - Copilot will create a manifest with default settings in copilot/environments/staging/manifest.yml
    - You can use existing VPCs or ALB. In this case will use the default (Copilot will create for us.)
5 - Deploy Staging Environment
    - copilot env deploy --name staging
    - Copilot will create VPC, Subnets and Cluster for deployment    
6 - Create Database for app:
    - If you look at source_code/todoapp/settings.py, the code contains a section to connect to a Database:
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
    - copilot storage init -n todoapp-db -t Aurora -w todoapp-$REGION-main --engine PostgreSQL
    - When the Copilot asks for deletetion behavior, choose yes.
    - What would you like to name the initial database in your cluster? set todoappdb
    - Copilot will update environment variables in the service and we can get the valuess of the database using the
    - Environment variable TODOAPPDB_SECRET
7 Deploy Everything!
    - Now we can deploy all resources (Services, Databases, Docker Images, ECR Repository, Etc.)
    - The process take about 10 min to complete.
    - After the process complete, copilot will show you the url of the Loadbalancer Service:
        - You can access your service at http://<ALB Address> over the internet.
    - Access the service using this complete URL: http://<ALB Address>/todos/list (The main root URL dont access the service, this was set up on purpose)
    - <Put image of APP Running>
8 Adding More Services to our Application
    - Now we are going to add a pub/sub service to our application. So, exerytime a task is posted, we will put a task in a SQS Queue
    - A Consumer will read this and write to a DynamoDB.
    - Lets Add 2 services to you application: A BackEnd service, that will put events in SNS. And a Worker Service to act as a Consumer that will query a SQS Queue
    - copilot svc init --name producer-$REGION-sqs --svc-type "Backend Service" --dockerfile source_code/producer-sqs/Dockerfile
    - copilot svc init --name consumer-$REGION-sqs --svc-type "Worker Service" --dockerfile source_code/consumer-sqs/Dockerfile
    - Now, we will create a DynamoDB Table to consumer store results:
    - copilot storage init -t DynamoDB -n todoapp-table --partition-key ID:S --no-lsi --no-sort -w consumer-$REGION-sqs
    - Edit the manifest: copilot/producer-<REGION>-sqs/manifest.xml:
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
    - This will instruct copilot to create a SNS topic associated with a SQS Queue
    - On the same file, in network, add the private directive to turn ALB in private access only:
    network:
      connect: true # Enable Service Connect for intra-environment traffic between services.
      vpc:
        placement: private
    - Edit the file copilot/consumer-<REGION>-sqs/manifest.xml:
    subscribe:
      topics:
        - name: todoapp-topic
          service: producer-<REGION>-sqs
      queue:
        dead_letter:
          tries: 5
    - We are instructing the consumer service do access the Queue from the producer service.
    - Deploy the new services:
    - copilot svc deploy --name consumer-$REGION-sqs --env staging
    