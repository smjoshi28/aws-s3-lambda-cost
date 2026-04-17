import json
import boto3
import csv 
import io
import numpy as np 
import pandas as pd
import os 

s3 = boto3.client("s3")
sns = boto3.client("sns")

SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:ap-south-1:829058667760:mysnstopic')

def lambda_handler(event, context):
    try:
        # 1. Get bucket and file information
        bucketname = event["Records"][0]["s3"]["bucket"]["name"]
        bucketobject = event["Records"][0]["s3"]["object"]["key"]

        # 2. Fetch the CSV data
        response = s3.get_object(Bucket=bucketname, Key=bucketobject)
        data = response["Body"].read().decode("utf-8")

        # 3. Load into DataFrame
        df = pd.read_csv(io.StringIO(data))
        
        # 4. Filter 'Service total' and convert Service column to datetime for sorting
        daily_costs_df = df[df['Service'].apply(lambda x: x != 'Service total')].drop(columns=['Tax($)'], errors='ignore').copy()
        daily_costs_df['Service'] = pd.to_datetime(daily_costs_df['Service'])
        daily_costs_df = daily_costs_df.sort_values(by='Service')

        email_body = ""

        # --- ANALYSIS PART 1: TOTAL COST SPIKES ---
        total_costs = daily_costs_df['Total costs($)'].values
        q1_total, q3_total = np.percentile(total_costs, [25, 75])
        iqr_total = q3_total - q1_total
        upper_bound_total = q3_total + 1.5 * iqr_total
        
        # Calculate % change for Total Costs
        daily_costs_df['Total_Pct_Change'] = daily_costs_df['Total costs($)'].pct_change() * 100
        
        is_spike_total = lambda x: x > upper_bound_total
        daily_costs_df['Is_Spike'] = daily_costs_df['Total costs($)'].apply(is_spike_total)
        
        total_spikes = daily_costs_df[daily_costs_df['Is_Spike'] == True]
        
        if not total_spikes.empty:
            email_body += "=================== Total Cost Spikes ========================\n"
            for _, row in total_spikes.iterrows():
                pct_str = f"{row['Total_Pct_Change']:.2f}%" if not pd.isna(row['Total_Pct_Change']) else "N/A"
                email_body += f"Date: {row['Service'].date()}, Amount: ${row['Total costs($)']:.2f}, Increase from Prev Day: {pct_str}\n"

        # --- ANALYSIS PART 2: INDIVIDUAL SERVICE-WISE SPIKES ---
        service_cols = [col for col in daily_costs_df.columns if col not in ['Service', 'Total costs($)', 'Is_Spike', 'Total_Pct_Change']]
        
        svc_email_section = "\n=================== Cost Spikes for Services ========================\n"
        svc_spike_found = False

        for col in service_cols:
            col_values = daily_costs_df[col].values
            q1_svc, q3_svc = np.percentile(col_values, [25, 75])
            iqr_svc = q3_svc - q1_svc
            upper_bound_svc = q3_svc + 1.5 * iqr_svc
            
            # Calculate % change for this service
            pct_col_name = f"{col}_Pct_Change"
            daily_costs_df[pct_col_name] = daily_costs_df[col].pct_change() * 100
            
            svc_spikes = daily_costs_df[daily_costs_df[col] > upper_bound_svc]
            
            if not svc_spikes.empty:
                svc_spike_found = True
                for _, row in svc_spikes.iterrows():
                    pct_str = f"{row[pct_col_name]:.2f}%" if not pd.isna(row[pct_col_name]) else "N/A"
                    svc_email_section += f"{col} Spike: Date: {row['Service'].date()}, Amount: ${row[col]:.2f}, Increase: {pct_str}\n"

        if svc_spike_found:
            email_body += svc_email_section

        # 5. SEND EMAIL VIA SNS
        if email_body:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"Alert: AWS Cost Spike Detected - {bucketobject}",
                Message=email_body
            )

        return {
            'statusCode': 200,
            'body': json.dumps('Analysis completed and alert sent if spikes were found.')
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
