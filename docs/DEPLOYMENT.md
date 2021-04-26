## Deployment
This document covers steps on setting up this repository on various cloud hosting providers.

  - [AWS](#aws)

### AWS

#### Pre-requisites
Deploying on AWS requires a basic understanding of the following tools and services:
1. Docker
2. GitHub actions & workflows
3. GitHub environments and secrets
4. AWS Elastic Container Registry (ECR)
5. AWS Elastic Container Service (ECS)
6. AWS Virtual Private Cloud (VPC)
7. AWS Fargate
8. AWS Elastic Load Balancer (ELB)
9. AWS Elastic IPs
10. AWS Identity and Access Management (IAM)
11. AWS Relational Database Service (RDS)

#### Staging
Setting up staging environment on AWS is pretty straightforward.
1. Login to your AWS console.
2. Go to VPC. (skip this step if you've already created a VPC when setting up backend repository)
   1. Create a new VPC.
   2. Name it `plio-staging-vpc`.
   3. In IPv4 CIDR block, enter `10.0.0.0/28`.
   4. Click on create button. You will see the new VPC under the list of VPCs.
3. Set up database through RDS.
   1. Click on create database.
   2. Use "Standard create" in database creation method.
   3. Use Postgres12 in the DB engine.
   4. Under templates, go with "Production".
   5. Name the DB instance identifier as `plio`.
   6. Set the master user name and password.
   7. For DB instance, we can go with Burstable classes to get started with. Select the one having vCPUs & RAM as per your needs.
   8. Set the alloted storage as per your needs.
   9. For Availability and Durability, use multi-AZ deployment if you need. Take a note that this may almost double your monthly expense.
   10. Under VPC settings, select the VPC created in previous step.
   11. In case you prefer to connect to your database directly from your machine, set the public access to "Yes".
   12. Under additional configuration, set initial database name as `plio`. This will create an empty database.
   13. Create the RDS instance by clicking on "Create Database" button.
   14. You will see the new RDS instance in the list of RDS instances. Click on your DB instance to see the connectivity settings.
   15. To connect to RDS from command line, run the following command (this will work if you've set public access to yes):
   ```sh
   psql -h your-db-instance-endpoint.aws-region.rds.amazonaws.com -p 5432 -U master_username
   ```
4. Create a new Elastic IP by going to EC2 dashboard and navigating to Elastic IP section.
   1. Click on Allocate Elastic IP address and click on Allocate button.
   2. You will see a new IP address in the IPs list. Name it `plio-backend-staging`.
5. Go to Target groups.
   1. Create a new target group.
   2. Choose target type to be `IP addresses`.
   3. Name the target group as `plio-backend-staging`.
   4. Select the `plio-staging-vpc` for the target group VPC.
   5. Proceed to create target group. You will see target group in the list.
6. Go to Load Balancers.
   1. Create a new load balancer.
   2. Select Network Load Balancer option.
   3. Name the LB as `plio-backend-staging`.
   4. Select the `plio-staging-vpc` for the load balancer.
   5. In the subnet mappings, check the first desired zone and use Elastic IP under IPv4 settings for that subnet.
   6. Under listeners and routing, select the target group `plio-backend-staging` for TCP port 80.
   7. Proceed to create load balancer. You will see load balancer in the list.
7. Go to ECR and create a new repository named `plio-backend-staging`.
8. Now go to ECS and create a new task definition with name `plio-backend-staging`.
   1. Set the task role as `ecsTaskExecutionRole`.
   2. Set the task memory and task CPU based on your needs.
   3. Create a new container with name `plio-backend-staging`.
   4. Enter port `80` in the port mapping field.
   5. Use `.env.example` file to set all the required environment variables for your container.
   6. Save the container definition and the task definition.
   7. You will see the new task definition within the list.
9.  Go to clusters and create a new cluster with name `plio-staging-cluster`. (skip this step if you've already created a VPC when setting up backend repository)
   8. Use `Networking only` option
   9. Create a new VPC for your cluster.
   10. Click on create button.
   11. You will see the new cluster within the list of clusters.
10. Get into `plio-staging-cluster` and create a new service.
   12. Set launch type to Fargate. We'll use serverless deployments for Plio.
   13. Name the service as `plio-staging-backend`.
   14. Under task definition, select `plio-backend-staging` and use latest revision.
   15. Number of tasks to be one.
   16. Service type to be `REPLICA`.
   17. Minimum healthy percentage should be 100 and maximum percent to be 200.
   18. Deployment type to be `rolling update`.
   19. Keep other values as default.
   20. Use the Cluster VPC and the subnet that you configured with Elastic IP.
   21. Auto-assign public IP to have `ENABLED`.
   22. Under load balancing, select the Network Load Balancing option and select the `plio-backend-staging` load balancer.
   23. Inside "Container to Load Balancer", click on Add to load balancer option and select `plio-backend-staging` in the target group.
   24. For auto-scaling, go with "Do not adjust the service's desired count" for staging.
   25. Review and create service.
11. Next, go to your GitHub repository and create a new environment from settings tab.
    1. Name the environment as `Staging`.
    2. Make sure you have added the following GitHub secrets on repository level. If not, add these as your environment secrets.
       - AWS_ACCESS_KEY_ID
       - AWS_SECRET_ACCESS_KEY
       - AWS_REGION
12. Once done, make some changes to the code so that the GitHub workflow `deploy_to_ecs_staging.yml` gets triggered.


#### Production
Setting up a production environment on AWS is same as staging. Take care of the following things:
1. Rename all services to have `plio-backend-production` or similar naming convention.
2. Go with auto-scaling option when creating a new service from ECS.
