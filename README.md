# aws-copilot-demo
Demo do funcionamento do AWS Copilot

Requisitos:
    - AWS CLI
    - Copilot CLI
    - Docker
    - AWS Permissions (Temp creds ou Instance Role)

Install Copilot CLI
    - https://aws.github.io/copilot-cli/docs/getting-started/install/

Initialize APP
    - copilot init --app todoapp --dockerfile source_code/main/Dockerfile --name todoapp-main --type  "Load Balanced Web Service"
    - When Copilot asks to deploy into a test environment, choose N.


