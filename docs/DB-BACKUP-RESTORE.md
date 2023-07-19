# Note of backing up and restoring postgres DB
- There are times where one might need to take a backup of both staging and prod db and maybe restore it to another RDS instance.
- Follow the following steps to achieve this. You'll be prompted to put in your password in all of these commands
  - Take dump of staging and prod db
  ```sh
  pg_dump -Fc -v -h YOUR_SOURCE_RDS_INSTANCE_ENDPOINT -U YOUR_USERNAME plio_staging > plio_staging.dump
  pg_dump -Fc -v -h YOUR_SOURCE_RDS_INSTANCE_ENDPOINT -U YOUR_USERNAME plio_production > plio_production.dump
  ```
  - Restore db dump to another dbs
  ```sh
  pg_restore -v -h YOUR_DESTINATION_RDS_INSTANCE_ENDPOINT -U YOUR_USERNAME -d plio_staging plio_staging.dump
  pg_restore -v -h YOUR_DESTINATION_RDS_INSTANCE_ENDPOINT -U YOUR_USERNAME -d plio_production plio_production.dump
  ```
- It's possible that you might need to create new dbs in the destination db where you're trying to restore the data. Follow these steps below to achieve that.
  - Login to the rds
  ```sh
  psql -h YOUR_DESTINATION_RDS_INSTANCE_ENDPOINT -U YOUR_USERNAME
  ```
  - Enter your password when prompted
  - Run `CREATE DATABASE "plio_staging";` and `CREATE DATABASE "plio_production";` to create the dbs and then run the restore command as highlighted above.
