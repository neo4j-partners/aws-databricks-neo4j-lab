# Databricks Workspace Setup

Follow these steps to sign in to the workshop Databricks workspace and prepare your environment.

## Step 1 — Accept the Workspace Invitation

You received an email inviting you to collaborate in a Databricks workspace. Click the link in the email to open the Databricks sign-in page.

On the sign-in page, select **Sign in with email**. Databricks will send a one-time passcode (OTP) to your email address. Check your inbox, copy the code, and enter it on the sign-in page to complete authentication.

> **Tip:** The passcode expires after a few minutes. If it expires, request a new one from the sign-in page.

## Step 2 — Verify Your Compute Cluster

Once logged in, click **Compute** in the left sidebar. You should see a personal compute cluster that has been pre-configured for you by the workshop admin (e.g., `lab-<yourname>`). Confirm it is available before proceeding.

![Compute overview showing your personal cluster](images/compute_overview.png)

## Step 3 — Clone the Lab Notebooks

Navigate to **Workspace** in the left sidebar. Expand **Shared > aws-databricks-neo4j-lab > labs**. Right-click on the `labs` folder and select **Clone**.

![Right-click the labs folder and select Clone](images/03_clone.png)

## Step 4 — Configure the Clone Destination

In the Clone dialog:

1. Update the **New name** to include your initials (e.g., `labs-rk`).
2. Select the **For you** tab.
3. Choose your home directory as the destination.
4. Click **Clone**.

![Clone dialog — rename and select your home directory](images/04_clone_labs.png)

## Step 5 — Attach Your Compute Cluster

Open the first notebook, `01_aircraft_etl_to_neo4j.ipynb`, from your cloned folder. Click the compute selector in the top-right of the notebook and select your personal compute cluster from the list under **Active resources**.

![Select your personal compute cluster from the dropdown](images/6-change-compute-your-compute.png)

## Step 6 — Enter Your Neo4j Connection Details

In the notebook's **Configuration** cell near the top, update the Neo4j connection variables with the credentials from your Lab 1 Aura setup:

```python
NEO4J_URI = "neo4j+s://xxxxxxxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "<your-password>"
```

## Step 7 — Run the Notebook

Click **Run all** in the toolbar to execute the entire notebook. Monitor the cell outputs for any errors.
