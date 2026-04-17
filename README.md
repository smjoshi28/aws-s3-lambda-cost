# AWS Cost Spike Detector (Lambda)

An automated serverless solution that monitors AWS cost reports stored in S3, analyzes them for statistical anomalies using the **Interquartile Range (IQR)** method, and sends alerts via **Amazon SNS**.

## 🚀 Overview

This Lambda function is triggered whenever a new cost CSV file is uploaded to a specific S3 bucket. It performs two levels of analysis:
1.  **Total Cost Spikes:** Detects if the overall daily spend is statistically higher than normal.
2.  **Service-Specific Spikes:** Breaks down individual AWS services (e.g., EC2, S3, RDS) to find which specific resource caused a price jump.

## 🛠 Architecture

* **S3:** Stores the daily/monthly cost breakdown CSVs.
* **AWS Lambda:** Processes the data using `pandas` and `numpy`.
* **Amazon SNS:** Dispatches email alerts when spikes are detected.
* **Environment Variables:** Uses `SNS_TOPIC_ARN` for flexible deployments.

## 📊 Statistical Method: IQR

The script uses the **Interquartile Range (IQR)** to define outliers. 

* **Q1 (25th percentile):** The middle of the first half of the data.
* **Q3 (75th percentile):** The middle of the second half of the data.
* **Threshold:** Any cost exceeding $Q3 + 1.5 \times (Q3 - Q1)$ is flagged as a spike.

## 📋 Prerequisites

* **Python 3.x**
* **AWS Lambda Layers:** Since `pandas` and `numpy` are not native to Lambda, you must add a Layer (like the [Klayers](https://github.com/keithrozario/Klayers) or the AWS SDK Pandas layer).
* **S3 Trigger:** Configure your bucket to trigger this Lambda on `s3:ObjectCreated:*` events.

## ⚙️ Installation & Setup

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/your-username/aws-cost-spike-detector.git
    ```
2.  **Deploy Lambda:**
    * Upload the code to a Python 3.9+ Lambda function.
    * Attach a policy allowing `s3:GetObject` and `sns:Publish`.
3.  **Set Environment Variables:**
    * `SNS_TOPIC_ARN`: The ARN of your SNS Topic.
4.  **Configure SNS:**
    * Create an SNS Topic.
    * Subscribe your email address to the topic and confirm the subscription.

## 📧 Sample Alert Output

When a spike is detected, you will receive an email like this:

```text
=================== Total Cost Spikes ========================
Date: 2026-04-15, Amount: $145.20, Increase from Prev Day: 305.00%

=================== Cost Spikes for Services ========================
AmazonEC2 Spike: Date: 2026-04-15, Amount: $120.00, Increase: 450.00%
```
