# Deploy and Run FastAPI Application on EC2 with GitHub Actions

This guide outlines the steps to deploy and run a FastAPI application on an EC2 instance using GitHub Actions for CI/CD. The deployment process involves setting up the EC2 instance, configuring SSH keys, creating GitHub Actions workflows, and setting up Nginx for reverse proxy.

## Prerequisites

- AWS account
- GitHub repository
- Basic knowledge of Git, Docker, and SSH

## Steps

### 1. Launch EC2 Instance

1. **Launch an EC2 Instance with Ubuntu:**
   - Open the EC2 Dashboard in AWS Management Console.
   - Click on "Launch Instance".
   - Choose an Ubuntu AMI.
   - Select the instance type and configure instance details as needed.
   - Add storage and configure security group to allow SSH (port 22) and HTTP (port 80) access.
   - Launch the instance and download the key pair (.pem file).

2. **Create an IAM Role:**
   - Go to the IAM Dashboard and click on "Roles".
   - Click on "Create Role".
   - Select EC2 from the service or use case options.
   - Attach the `AmazonEC2RoleforAWSCodeDeploy` policy.
   - Name the role and create it.

3. **Attach IAM Role to EC2 Instance:**
   - Go to the EC2 Dashboard and select your instance.
   - Click on "Actions" > "Security" > "Modify IAM role".
   - Choose the IAM role you created and update the IAM role.

### 2. Create a GitHub SSH Key

1. **Generate SSH Key:**
   - Run the following command to generate a new SSH key:
     ```sh
     ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_github
     ```
   - Follow the prompts and set a passphrase if desired.

2. **Add SSH Key to GitHub:**
   - Run the following command to display the public key:
     ```sh
     cat ~/.ssh/id_github.pub
     ```
   - Copy the content of the public key.
   - Go to GitHub > Settings > SSH and GPG keys.
   - Click on "New SSH Key", give it a title, and paste the public key.

### 3. Create a GitHub Action Workflow

1. **Set Up Workflow:**
   - Go to your GitHub repository.
   - Click on "Actions" > "set up a workflow yourself".
   - Rename the file to `deploy.yml` and click on "Commit changes".

2. **Create a Dockerfile:**
   - Create a `Dockerfile` in the root directory of your repository:
     ```Dockerfile
     
      FROM python:3.9-slim

      WORKDIR /app

      COPY . /app

      RUN pip install --no-cache-dir -r requirements.txt

      EXPOSE 80 
      
      CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

     ```

3. **Create the `deploy.yml` File:**
   ```yaml
   name: Deploy FastAPI to EC2

   on:
     push:
       branches:
         - dev  # Trigger the workflow on push to the 'dev' branch

   jobs:
     deploy:
       runs-on: ubuntu-latest

       steps:
         - name: Checkout code
           uses: actions/checkout@v2  # Checkout the repository code

         - name: Set up Python
           uses: actions/setup-python@v2  # Set up Python environment
           with:
             python-version: '3.9'

         - name: Install dependencies
           run: |
             python -m pip install --upgrade pip  # Upgrade pip
             pip install -r requirements.txt  # Install Python dependencies

         - name: Add SSH key
           uses: webfactory/ssh-agent@v0.5.3  # Add SSH key to access EC2 instance
           with:
             ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

         - name: Add EC2 host to known hosts
           run: |
             ssh-keyscan -H ${{ secrets.EC2_HOST }} >> ~/.ssh/known_hosts  # Add EC2 host to known hosts for SSH

         - name: Stop existing Uvicorn process on EC2
           run: |
             ssh ${{ secrets.EC2_USER }}@${{ secrets.EC2_HOST }} "sudo pkill -f uvicorn"  # Stop any running Uvicorn processes on EC2

         - name: Copy files via SSH
           run: |
             scp -r ./* ${{ secrets.EC2_USER }}@${{ secrets.EC2_HOST }}:/home/ubuntu/  # Copy repository files to EC2 instance

         - name: Install python3-venv on EC2
           run: |
             ssh ${{ secrets.EC2_USER }}@${{ secrets.EC2_HOST }} "sudo apt-get update && sudo apt-get install -y python3-venv"  # Install python3-venv on EC2

         - name: Create virtual environment and install dependencies on EC2
           run: |
             ssh ${{ secrets.EC2_USER }}@${{ secrets.EC2_HOST }} "python3 -m venv /home/ubuntu/venv"  # Create Python virtual environment
             ssh ${{ secrets.EC2_USER }}@${{ secrets.EC2_HOST }} "/home/ubuntu/venv/bin/pip install --upgrade pip"  # Upgrade pip in virtual environment
             ssh ${{ secrets.EC2_USER }}@${{ secrets.EC2_HOST }} "/home/ubuntu/venv/bin/pip install -r /home/ubuntu/requirements.txt"  # Install dependencies in virtual environment

         - name: Run FastAPI with Uvicorn
           run: |
             ssh ${{ secrets.EC2_USER }}@${{ secrets.EC2_HOST }} "nohup /home/ubuntu/venv/bin/uvicorn main:app --host 0.0.0.0 --port 80 &"  # Start Uvicorn server with FastAPI

   ```

### 4. Create EC2 SSH Key

1. **Generate EC2 SSH Key:**
   - SSH into your EC2 instance.
   - Run the following command to generate a new SSH key:
     ```sh
     ssh-keygen -t rsa -b 2048 -f ~/.ssh/my-ec2-key
     ```

2. **Add Public Key to Authorized Keys:**
   - Run the following commands to add the public key to the authorized keys:
     ```sh
     cp ~/.ssh/my-ec2-key.pub ~/.ssh/authorized_keys
     chmod 700 ~/.ssh
     chmod 600 ~/.ssh/authorized_keys
     ls -ld ~/.ssh
     ls -l ~/.ssh/authorized_keys
     ```

3. **Copy Private Key:**
   - Run the following command to display the private key:
     ```sh
     cat ~/.ssh/my-ec2-key
     ```
   - Copy the content of the private key.

### 5. Add Secrets to GitHub

1. **Add Secrets:**
   - Go to your GitHub repository.
   - Click on "Settings" > "Secrets and variables" > "Actions".
   - Add the following secrets:
     - `EC2_HOST`: Public IP address of your EC2 instance
     - `EC2_USER`: `ubuntu`
     - `SSH_PRIVATE_KEY`: Content of `my-ec2-key`

2. **Push Code to GitHub:**
   - Push your code to the branch specified in the GitHub Actions workflow (`dev`).

3. **Check GitHub Actions:**
   - Go to the "Actions" tab in your GitHub repository.
   - Ensure each stage of the workflow passes correctly.

### 6. Install and Configure Nginx

1. **Install Nginx:**
   - SSH into your EC2 instance and run the following commands:
     ```sh
     sudo apt-get update
     sudo apt-get install nginx
     ```

2. **Configure Nginx:**
   - Create a configuration file for your FastAPI app:
     ```sh
     sudo nano /etc/nginx/sites-available/fastapi
     ```
   - Add the following content to the file:
     ```nginx
     server {
         listen 80;
         server_name 184.72.145.xxx;  # Replace with your EC2 public IP or DNS

         location / {
             proxy_pass http://127.0.0.1:80;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
             proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
             proxy_set_header X-Forwarded-Proto $scheme;
         }
     }
     ```

3. **Enable Configuration and Restart Nginx:**
   - Enable the configuration and restart Nginx:
     ```sh
     sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled
     sudo nginx -t
     sudo systemctl start nginx `For first time`
     sudo systemctl reload nginx
     sudo systemctl status nginx
     sudo tail -n 20 /var/log/nginx/error.log

     ```

### 7. Access Your Application

- Open a browser and navigate to the public IP address of your EC2 instance. Your FastAPI application should be running.

### 8. To run code on local
- `uvicorn main:app`

### 9. APIs Endpoints
0. `/test`  - Root 
1. `/ambcryptoScrapped` 
2. `/coinDeskScrapped`
3. `/coinGapeScrapped`
4. `/cryptoPotatoScrapped`
5. `/forbesScrapped`
6. `/theDefiantScrapped`
7. `/watcherGuruScrapped`

### 10. Check uvicorn on EC2 Instance
1. Check logs: `tail -f /home/ubuntu/uvicorn.log`
2. Stop server: `sudo pkill -f uvicorn`
3. Verify server is stopped: `ps aux | grep uvicorn`
4. Start server: `sudo nohup /home/ubuntu/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 > /home/ubuntu/uvicorn.log 2>&1 &`

## Conclusion

By following these steps, you have successfully deployed a FastAPI application on an EC2 instance using GitHub Actions for continuous deployment and Nginx as a reverse proxy. This setup ensures an automated and efficient deployment process for your application.
