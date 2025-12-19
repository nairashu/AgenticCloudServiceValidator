# AgenticCloudServiceValidator
Cloud services are today built driving goal states and could have multiple dependencies between services to maintain states.
The aim of this project to is build an AI application that spins up Agents to perform validations against your dependencies.
Features:
1. The app should be lightweight and deployed on managed Kubernetes
2. The user should be able to define which service is being validated and what are the dependent services.
3. Users need to provide the authentication and authorization required by the Agent to access the goal state for the dependent services
4. User will define the timelines to run periodical verification of their backend data.
5. The application will spin up agents to:
    1) Fetch the data from dependencies
    2) Cross-verify the data across dependencies
    3) Maintain reports of anaomalies (Backend data)
    4) Alert users when anamolies are beyond thresholds
6. The application will also have a UI Dashboard to visualize the report using Grafana.

