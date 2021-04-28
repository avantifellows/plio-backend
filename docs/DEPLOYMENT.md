## Deployment
This document covers the steps on setting up this repository on various cloud hosting providers.

  - [AWS](#aws)

# AWS

## Pre-requisites

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

## Staging

### Continuous Delivery process

An overview of how the continuous delivery cycle works in Plio with GitHub action and Amazon ECR & ECS.

![Overview of Continuous Delivery process](images/aws-gh-cd.png)

Follow the steps below to set up the staging environment on AWS.

1. Login to your AWS console.

2. Go to VPC. (skip this step if you've already created a VPC when setting up the frontend repository)
   1. Create a new VPC.
   2. Name it `plio-staging`.
   3. In IPv4 CIDR block, enter `10.0.0.0/16` - this will reserve 255 * 255 IPs within the VPC.
   4. Click on the create button. You will see the new VPC under the list of VPCs.
   5. Check out this [AWS guide for more details on VPC](https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html).

   6. You'll need to attach an Internet Gateway to this VPC.
      1. Click on `Internet Gateways` in the VPC Dashboard.
      2. Select `Create internet Gateaway`.
      3. Name it as `plio-staging` and save it.
      4. Click on `Attach to a VPC` in the next page and select the VPC created above.

   7. Next, you'll need to attach Subnets to the VPC created above.
      1. Click on `Subnets` in the VPC Dashboard.
      2. Click on `Create Subnet`.
      3. Choose the VPC created above as VPC ID.
      4. Enter the `Subnet name` as `plio-staging-1`.
      5. Either choose the `Availability Zone` if you have a preference or leave it to the default
      6. Under `IPv4 CIDR block`, add a range of IPv4s that belong to your subnet. If you followed the steps above exactly, you can set this value as `10.0.0.0/24`. This will reserve the IPs `10.0.0.0` to `10.0.0.255` to this Subnet.
      7. If you want to, you can create more subnets using `Add new subnet`  but it's not needed going forward. If you do choose to do so, you'll need to choose a different non-overlapping range of IPv4s for the `IPv4 CIDR block` option - for example, you could set it to: `10.0.1.0/24` to reserve the  IPs `10.0.1.0` to `10.0.1.255`.
      8. Finally, create the subnet.

   8. You need to update your `Route Tables` to give make your subnets publicly accessible.
      1. Click on `Route Tables` in the VPC Dashboard
      2. Select the entry corresponding to the VPC you created above.
      3. Navigate to the `Routes` tab.
      4. Click on `Edit routes`.
      5. Click on `Add route`.
      6. Add `0.0.0.0/0` as the `Destination`.
      7. Select `Internet Gateway` under `Target` and link to the Internet Gateway you created above.
      8. Click on `Save routes`.

6. Set up the database. Click on `Databases` on the AWS RDS page.
   1. Click on `Create Database`.
   2. Use `Standard create` the in database creation method.
   3. Use Postgres12 in the DB engine.
   4. Under templates, go with `Production`.
   5. Name the DB instance identifier as `plio`.
   6. Set the master user name and password.
   7. For DB instance, we can go with Burstable classes to get started with. Select the one having vCPUs & RAM as per your needs.
   8. Set the alloted storage as per your needs.
   9. For Availability and Durability, use multi-AZ deployment if you need. Take a note that this may almost double your monthly expense.
   10. Under VPC settings, select the VPC created in previous step.
   11. In case you prefer to connect to your database directly from your machine, set the public access to "Yes".
   12. Under additional configuration, set initial database name as `plio_staging`. This will create an empty database.
   13. Finally, create the RDS instance by clicking on "Create Database" button.
   14. You will see the new RDS instance in the list of RDS instances. Click on your DB instance to see the connectivity settings.
   15. To connect to RDS from command line, run the following command (this will work if you've set public access to yes):
   ```sh
   psql -h your-db-instance-endpoint.aws-region.rds.amazonaws.com -p 5432 -U master_username
   ```
   16. Once you are logged in into the PSQL CLI, you can run all the SQL commands to create a new database, user, grant privileges etc.

7. Create a new Elastic IP by going to EC2 dashboard and navigating to the `Elastic IP` section.
   1. Click on `Allocate Elastic IP address` and click on `Allocate` .
   2. You will see a new IP address in the IPs list. Name it `plio-backend-staging`.
   3. This will be used in later steps to give the load balancer a permanent IP address.

8. Go to Target groups.
   1. Create a new target group.
   2. Choose target type to be `IP addresses`.
   3. Name the target group as `plio-backend-staging`.
   4. Set the protocol to `TCP` and port to `80`.
   5. Select the `plio-staging` for the target group VPC.
   6. In the next step, add an IP address in the `IP` text area - the IP address should belong to your VPC - if you followed the steps above exactly, you can use any IP address between `10.0.0.0` to `10.0.255.255`.
   7. Proceed to create the target group. You will see the created target group in the list of all target groups.

9. Go to Load Balancers (LBs).
   1. Create a new load balancer.
   2. Select `Network Load Balancer` option. We use NLB for easy support of web socket connections.
   3. Name the LB as `plio-backend-staging`.
   4. Select the `plio-staging` VPC for the load balancer.
   5. In the subnet mappings, check the first desired zone and use Elastic IP under IPv4 settings for that subnet.
   6. Under listeners and routing, select the target group `plio-backend-staging` for TCP port 80.
   7. Proceed to create the load balancer. You will see the created load balancer in the list of all load balancers.

10. Go to ECR and create a new repository named `plio-backend-staging` and set the settings as per your needs.

11. Now go to ECS and create a new task definition

    1. Select Fargate and name the task definition as `plio-backend-staging`.
    2. Set the task role as `ecsTaskExecutionRole`.
    3. Set the task memory and task CPU based on your needs. Good defaults to use are: 2 GB for memory and 0.5 vCPU.
    4. Create a new container with name `plio-backend-staging`.
    5. In the image field, you can just type in `image_arn`. This is not a valid entry and just a placeholder for now as it'll be replaced by the actual image ARN once the GitHub workflow triggers.
    6. Enter port `80` in the port mapping field.
    7. Use the `.env.example` file to set all the required environment variables for your container in the `Environment Variables` section.
    8. Save the container definition and the task definition.
    9. You will see the new task definition within the list of all task definitions.

12. Go to `Clusters` and create a new cluster with the name `plio-staging-cluster`. (skip this step if you've already created a VPC when setting up the frontend repository)
    1. Select `Networking only`. We will go with serverless deployment so that we don't worry about managing our own server instances.
    2. Don't create a new VPC for your cluster. We'll use the VPC created in previous step in the next step of creating a service.
    3. Click on the create button.
    4. You will see the new cluster within the list of clusters.

13. Get into `plio-staging-cluster` and create a new service.

       1. Set launch type to Fargate. We'll use serverless deployments for Plio.
       2. Name the service as `plio-backend-staging`.
       3. Under task definition, select `plio-backend-staging` and use latest revision.
       4. Set the number of tasks to be one.
       5. Service type to be `REPLICA`.
       6. Minimum healthy percentage should be 100 and maximum percent to be 200. Minimum healthy percentage defines the percentage of tasks that should be running at all times. Maximum percent defines how many additional tasks the service can create in parallel to running tasks, before killing the running tasks.
       7. Deployment type to be `rolling update`.
       8. Keep other values as default.
       9. Use the Cluster VPC and the subnet that you configured previously with Elastic IP.
       10. Set Auto-assign public IP to `ENABLED`. Otherwise, it makes the task accessible only through VPC and not public.
       11. Under load balancing, select the `Network Load Balancing` option and select the `plio-backend-staging` load balancer.
       12. Inside `Container to Load Balancer`, click on `Add to load balancer option` and select `plio-backend-staging` in the target group.
       13. For auto-scaling, go with `Do not adjust the service's desired count`  for staging.
       14. Review and create the service.

14. Next, go to your GitHub repository and create a new environment from the settings tab.
    1. Name the environment as `Staging`.
    2. Make sure you have added the following GitHub secrets on repository level. If not, add these as your environment secrets.
       - AWS_ACCESS_KEY_ID
       - AWS_SECRET_ACCESS_KEY
       - AWS_REGION

15. We are using Github Actions to trigger deployments. You can find the workflow defined in `.github/workflows/deploy_to_ecs_staging.yml`. It defines a target branch such that a deployment is initiated whenever a change is pushed to the target branch.

16. Once done, push some changes to the target branch so that the GitHub workflow `deploy_to_ecs_staging.yml` gets triggered.


#### Production
Setting up a production environment on AWS is almost the same as staging. Additionally, take care of the following things:
1. Rename all services as `plio-backend-production` or a similar naming convention.
2. Go with auto-scaling option when creating a new service from ECS.
   1. When creating a service or when updating it, navigate to the service auto-scaling section.
   2. Select `Configure Service Auto Scaling to adjust your service's desired count`.
   3. Set minimum number of tasks to `1`. This is the minimum count of running tasks when scale-in operation happen.
   4. Set desired number of tasks to `1`. This may come pre-populated if you had set it before.
   5. Set maximum number of tasks to `2` or more based on your desired need. This is the maximum count of total running tasks in case of scale-out operation.
   6. In IAM role for Service Auto Scaling, select `AWSServiceRoleForApplicationAutoScaling_ECSService`.
   7. Click on `Add scaling policy`.
   8. Select policy type to `Target tracking`.
   9. Set policy name to `plio-backend-production-autoscaling-cpu`.
   10. In the ECS service metric, select the option for average CPU utilization.
   11. Target value should be `60` (or as per your requirement). This is the threshold value when the service will trigger a new event and perform scale-out operation.
   12. Scale-out & Scale-in cooldown period to be `300` seconds.
   13. `Disable scale-in` to remain unchecked.
   14. Save the scaling policy.
   15. Create or update the service name.
   16. Use [k6.io](https://k6.io/) or other load testing tool to check if auto-scaling is working fine or not. You can lower down the target threshold for testing purposes.
